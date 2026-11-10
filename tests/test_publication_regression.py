"""Regressions through real binding, generation, review and normal entry point."""
import copy
import json
import os
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import config
import editorial
import news_bot as bot
from tests.test_editorial import article, item


class PublicationRegressionTests(unittest.TestCase):
    def test_wrong_working_directory_cannot_create_another_outbox(self):
        original = os.getcwd()
        with tempfile.TemporaryDirectory() as temporary:
            try:
                os.chdir(temporary)
                with patch.object(bot, "_run") as run, patch.object(bot, "execution_lock") as lock:
                    self.assertEqual(bot.main(), 4)
                    run.assert_not_called()
                    lock.assert_not_called()
            finally:
                os.chdir(original)

    def test_escaped_panorama_and_long_whitespace_format_without_text_loss(self):
        from message_format import split_html, size
        import html
        import re
        for text in ("&" * 1000, "A" + "\n" * 4000 + "B"):
            with self.subTest(kind=text[:1]):
                fragments = split_html("<i>" + html.escape(text) + "</i>", 4016)
                self.assertTrue(all(size(part) <= 4016 for part in fragments))
                restored = html.unescape("".join(re.sub(r"</?i>", "", part) for part in fragments))
                self.assertEqual(restored, text)

    def test_final_word_budget_includes_automatic_labels_and_is_stable(self):
        for recap in (False, True):
            for body in (False, True):
                for delta in (-1, 0, 1):
                    with self.subTest(recap=recap, body=body, delta=delta):
                        source = article()
                        source["previously_sent"] = recap
                        if body:
                            source["body"] = "evidencia " * 110
                        raw = item(source)
                        raw.update(titulo="Decisão", contexto="", limitacao=None)
                        cap = 180 if body else 60
                        added = (5 if recap else 0) + (0 if body else 10)
                        raw["resumo_desenvolvido"] = " ".join(["fato"] * (cap + delta - added - 1))
                        bound = bot.bind_item(raw, [source])
                        if delta > 0:
                            self.assertIsNone(bound)
                        else:
                            self.assertIsNotNone(bound)
                            self.assertEqual(sum(len((bound[k] or "").split()) for k in editorial.TEXT_FIELDS), cap + delta)
                            self.assertEqual(bot.bind_item(bound, [source]), bound)
                            if not body:
                                self.assertIn("RSS", bound["limitacao"])

    def test_explicit_limitation_and_multiple_evidence_are_preserved(self):
        sources = [article(1), article(2)]
        raw = item(sources[0])
        raw["evidence_ids"].append(sources[1]["id"])
        bound = bot.bind_item(raw, sources)
        self.assertEqual(bound["limitacao"], raw["limitacao"])
        self.assertEqual(bot.bind_item(bound, sources), bound)

    def test_excluded_malformed_duplicate_does_not_poison_eligible_item(self):
        sources = [article(1), article(2)]
        forbidden = item(sources[0])
        forbidden["resumo_desenvolvido"] = "excesso " * 200
        with patch.object(bot, "call_gemini_json", return_value={"noticias": [forbidden, item(sources[1])]}):
            result = bot.summarize_with_ai(sources, False, excluded_ids={sources[0]["id"]})
        self.assertEqual([n["article_id"] for n in result["noticias"]], [sources[1]["id"]])
        self.assertEqual(result["invalid_ids"], [])

    def test_unknown_or_malformed_main_id_is_technical(self):
        for ident in ("unknown", None, [], {}, 7, True):
            with self.subTest(ident=ident):
                raw = item(article())
                raw["article_id"] = ident
                with patch.object(bot, "call_gemini_json", return_value={"noticias": [raw]}):
                    self.assertIsNone(bot.summarize_with_ai([article()], False))

    def test_duplicate_main_id_cannot_overwrite_invalid_category(self):
        source = article()
        invalid = item(source)
        invalid["resumo_desenvolvido"] = "excesso " * 200
        duplicate = dict(invalid, pais=None)
        with patch.object(bot, "call_gemini_json", return_value={"noticias": [invalid, duplicate]}):
            result = bot.summarize_with_ai([source], False)
        self.assertEqual(result["invalid_ids"], [source["id"]])
        self.assertEqual(result["invalid_categories"], {source["id"]: "BR"})

    def test_invalid_category_uses_known_subject_for_replacement(self):
        source = article()
        for country in (None, "INVALID", []):
            with self.subTest(country=country):
                raw = item(source)
                raw["pais"] = country
                with patch.object(bot, "call_gemini_json", return_value={"noticias": [raw]}):
                    result = bot.summarize_with_ai([source], False)
                self.assertEqual(result["invalid_categories"], {source["id"]: "BR"})

    def test_rejected_primary_can_still_be_auxiliary_evidence(self):
        sources = [article(1), article(2)]
        raw = item(sources[1])
        raw["evidence_ids"].append(sources[0]["id"])
        with patch.object(bot, "call_gemini_json", return_value={"noticias": [raw]}):
            result = bot.summarize_with_ai(sources, False, excluded_ids={sources[0]["id"]})
        self.assertEqual(result["noticias"][0]["evidence_ids"], raw["evidence_ids"])

    def run_normal_entry(self, sources, generation_batches, phases, reject_first=None, tamper_final=False):
        """Finite Gemini script. Actual binding, review, hashes, formatting and outbox run."""
        events = {a["id"]: "event-" + str(i) for i, a in enumerate(sources)}
        phases = iter(phases)
        batches = iter(generation_batches)
        generation_payloads = []
        review_count = 0
        def respond(serialized, **kwargs):
            nonlocal review_count
            payload = json.loads(serialized)
            phase = next(phases)  # unexpected calls fail
            if phase == "generate":
                self.assertIn("eligible_ids", payload)
                generation_payloads.append(payload)
                data = {"noticias": next(batches)}
            elif phase == "panorama":
                self.assertIn("noticias", payload)
                self.assertNotIn("rascunho", payload)
                data = {"panorama": "Sete decisões oficiais em acontecimentos distintos."}
            else:
                self.assertIn("rascunho", payload)
                review_count += 1
                reviews = []
                for n in payload["rascunho"]["noticias"]:
                    self.assertIn(n["article_id"], events)
                    reject = review_count == 1 and n["article_id"] == reject_first
                    reviews.append(dict(article_id=n["article_id"], version=payload["versions"][n["article_id"]],
                        status="rejeitada" if reject else "aprovada", motivo="Evento duplicado." if reject else None,
                        correcao=None, evento_id=events[n["article_id"]], duplicada_de=None, fonte_suspeita=False))
                data = dict(conjunto_version=payload["conjunto_version"], panorama_version=payload["panorama_version"],
                            acontecimentos_distintos=True, panorama_ok=True, panorama_observacao=None, revisoes=reviews)
                if tamper_final and payload["rascunho"]["panorama"]:
                    data["conjunto_version"] = "stale"
            return SimpleNamespace(text=json.dumps(data, ensure_ascii=False))

        with tempfile.TemporaryDirectory() as temporary:
            history = Path(temporary) / "history.json"
            outbox = Path(temporary) / "delivery.json"
            sent = []
            def post(url, **kwargs):
                self.assertEqual(kwargs["json"]["chat_id"], "test-chat")
                sent.append(kwargs["json"]["text"])
                return SimpleNamespace(status_code=200, json=lambda: {"ok": True, "result": {
                    "message_id": len(sent), "chat": {"id": "test-chat"}}})
            with patch.object(config, "HISTORY_FILE", str(history)), \
                 patch.object(config, "DELIVERY_STATE_FILE", str(outbox)), \
                 patch.dict(os.environ, BOT_PERSIST_GIT="0", GITHUB_ACTIONS="false"), \
                 patch.object(bot, "execution_lock", side_effect=lambda: nullcontext()), \
                 patch.object(bot, "GEMINI_API_KEY", "dummy"), \
                 patch.object(bot, "TELEGRAM_CHAT_ID", "test-chat"), \
                 patch.object(bot, "TELEGRAM_BOT_TOKEN", "dummy"), \
                 patch.object(bot, "collect_all_articles", return_value=(copy.deepcopy(sources), [])), \
                 patch.object(bot, "enrich_candidates", side_effect=lambda values: values), \
                 patch.object(bot.genai, "GenerativeModel") as model, \
                 patch.object(bot.requests, "post", side_effect=post), \
                 patch.object(bot.time, "sleep"):
                model.return_value.generate_content.side_effect = respond
                outcome = bot.main()
            self.assertIsNone(next(phases, None), "script not fully exercised")
            state = json.loads(outbox.read_text(encoding="utf-8")) if outbox.exists() else None
            return outcome, state, sent, generation_payloads

    def test_normal_entry_publishes_seven_versioned_distinct_events(self):
        sources = [article(i, country) for i, country in enumerate(("MUNDO", "BR", "BR", "MUNDO", "BR", "MUNDO", "BR"), 1)]
        outcome, state, sent, _ = self.run_normal_entry(sources, [[item(a) for a in sources]],
                                                      ["generate", "review", "panorama", "review"])
        self.assertEqual(outcome, 0)
        edition = state["editions"][0]
        bulletin = edition["editorial"]["bulletin"]
        self.assertEqual(edition["status"], "complete")
        self.assertEqual(len(set(bulletin["approval"]["events"].values())), 7)
        self.assertTrue(bot.validate_publication(bulletin, edition["editorial"]["catalog"]))
        self.assertEqual(bulletin["shortages"], {"BR": 0, "MUNDO": 0})
        self.assertTrue(all(len(text.encode("utf-16-le")) // 2 <= config.TELEGRAM_MAX_CHARS for text in sent))

    def test_unreviewed_over_quota_candidate_remains_available_for_replacement(self):
        sources = [article(i, country) for i, country in enumerate(("BR", "MUNDO", "BR", "MUNDO", "BR", "MUNDO", "BR", "BR"), 1)]
        reserve = sources[-1]
        outcome, state, _, calls = self.run_normal_entry(sources,
            [[item(a) for a in sources], [item(sources[0]), item(reserve)]],
            ["generate", "review", "review", "generate", "review", "panorama", "review"],
            reject_first=sources[0]["id"])
        self.assertEqual(outcome, 0)
        self.assertIn(reserve["id"], calls[1]["eligible_ids"])
        self.assertIn(sources[0]["id"], calls[1]["excluded_ids"])
        self.assertIn(reserve["id"], state["editions"][0]["editorial"]["bulletin"]["approval"]["items"])

    def test_final_approval_mismatch_blocks_normal_entry(self):
        sources = [article(i, "BR" if i < 5 else "MUNDO") for i in range(1, 8)]
        outcome, state, sent, _ = self.run_normal_entry(sources, [[item(a) for a in sources]],
            ["generate", "review", "panorama", "review"], tamper_final=True)
        self.assertEqual(outcome, 4)
        self.assertIsNone(state)
        self.assertEqual(sent, [])
