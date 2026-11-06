"""Regressões da revisão posterior às 58 correções iniciais."""
import copy
import json
import os
import tempfile
import unittest
import xml.etree.ElementTree as ET
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import config
import news_bot as bot
import web_access as web
from delivery_state import DeliveryStore
from tests.test_editorial import article, item, approval
from tests.test_pipeline import stamped


URL = "https://g1.globo.com/politica/principal.ghtml"
OTHER = "https://g1.globo.com/politica/relacionada.ghtml"


def page(*nodes, extra="", canonical=URL):
    return (f'<link rel="canonical" href="{canonical}">'
            '<script type="application/ld+json">' + json.dumps({"@graph": list(nodes)}) +
            "</script>" + extra)


def entity(url, body, free=True, **extra):
    return {"@type": "NewsArticle", "url": url, "articleBody": body,
            "isAccessibleForFree": free, **extra}


class BodyIdentityTests(unittest.TestCase):
    def enrich(self, content):
        a = article()
        a.update(url=URL, id=bot.article_id(URL))
        with patch.object(web, "bounded_get", return_value=(content.encode(), URL, "text/html")):
            return web.enrich_candidates([a])[0]

    def test_related_longer_graph_body_is_not_attached_to_primary(self):
        result = self.enrich(page(entity(URL, "Corpo da matéria principal."),
                                  entity(OTHER, "Outra matéria relacionada. " * 20)))
        self.assertEqual(result["body"], "Corpo da matéria principal.")

    def test_conflicting_bodies_for_same_identity_are_rejected(self):
        result = self.enrich(page(entity(URL, "Primeiro corpo."), entity(URL, "Outro corpo incompatível.")))
        self.assertEqual(result["body"], "")
        self.assertEqual(result["evidence_level"], "excerpt")

    def test_unmatched_entity_is_never_used_even_when_alone(self):
        self.assertEqual(self.enrich(page(entity(OTHER, "Corpo de outra notícia.")))["body"], "")

    def test_main_entity_id_relative_url_and_canonical_identity(self):
        cases = [
            {"@id": URL + "#article"},
            {"mainEntityOfPage": {"@id": URL + "?utm_source=rss"}},
            {"url": "/politica/principal.ghtml"},
        ]
        for identity in cases:
            with self.subTest(identity=identity):
                node = {"@type": "NewsArticle", "articleBody": "Corpo identificado.",
                        "isAccessibleForFree": True, **identity}
                self.assertEqual(self.enrich(page(node))["body"], "Corpo identificado.")

    def test_related_restricted_entity_does_not_block_public_primary(self):
        result = self.enrich(page(entity(URL, "Corpo público."), entity(OTHER, "Corpo restrito.", False)))
        self.assertEqual(result["body"], "Corpo público.")

    def test_free_article_with_paywall_script_is_still_public(self):
        content = page(entity(URL, "Corpo livre com acesso público."),
                       extra='<script src="/assets/paywall.js"></script>')
        self.assertEqual(self.enrich(content)["body"], "Corpo livre com acesso público.")

    def test_primary_restriction_blocks_its_body_and_dom_fallback(self):
        content = page(entity(URL, "Texto restrito embutido.", False),
                       entity(OTHER, "Texto público relacionado."),
                       extra="<article><p>Não usar como fallback.</p></article>")
        self.assertEqual(self.enrich(content)["body"], "")


class FollowupMainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patch.object(config, "HISTORY_FILE", str(Path(self.tmp.name) / "history.json")).start()
        patch.object(config, "DELIVERY_STATE_FILE", str(Path(self.tmp.name) / "outbox.json")).start()
        patch.dict(os.environ, BOT_PERSIST_GIT="0", GITHUB_ACTIONS="false").start()
        patch.object(bot, "execution_lock", side_effect=lambda: nullcontext()).start()
        patch.object(bot, "TELEGRAM_CHAT_ID", "test-chat").start()
        patch.object(bot, "TELEGRAM_BOT_TOKEN", "test-token").start()
        patch("delivery_state.time.sleep").start()
        class FixedDate(datetime):
            @classmethod
            def now(cls, tz=None):
                instant = datetime(2026, 11, 6, 18, tzinfo=timezone.utc)
                return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)
        patch.object(bot, "datetime", FixedDate).start()
        self.addCleanup(patch.stopall)
        self.sources = [article()]
        self.data = stamped(dict(panorama="Decisão já revisada.", noticias=[item(self.sources[0])]), self.sources)
        self.data["shortages"] = dict(BR=3, MUNDO=3)

    def freeze(self, key):
        store = DeliveryStore()
        return store, store.create(key, [dict(text="edição congelada", article_ids=[self.sources[0]["id"]])],
                                   "test-chat", dict(bulletin=self.data, catalog=self.sources))

    def test_finishing_yesterday_collects_today_with_updated_history(self):
        self.freeze("2026-11-05")
        fresh = article(2)
        final = stamped(dict(panorama="Decisão de hoje.", noticias=[item(fresh)]), [fresh])
        final["shortages"] = dict(BR=3, MUNDO=3)
        with patch.object(bot, "collect_all_articles", return_value=(self.sources + [fresh], [])) as collect, \
             patch.object(bot, "enrich_candidates", side_effect=lambda a: a), \
             patch.object(bot, "build_reviewed_bulletin", return_value=final) as build, \
             patch.object(bot, "send_telegram_message", side_effect=[
                 dict(status="sent", message_id=1, chat_id="test-chat"),
                 dict(status="sent", message_id=2, chat_id="test-chat")]):
            self.assertEqual(bot.main(), 5)
        collect.assert_called_once()
        self.assertEqual([a["id"] for a in build.call_args.args[0]], [fresh["id"]])
        self.assertEqual([e["key"] for e in DeliveryStore().data["editions"]], ["2026-11-05", "2026-11-06"])

    def test_pending_or_uncertain_older_delivery_still_blocks_today(self):
        store, edition = self.freeze("2026-11-05")
        for status in ("pending", "uncertain"):
            with self.subTest(status=status):
                edition["parts"][0]["status"] = status
                store.checkpoint()
                with patch.object(bot, "collect_all_articles") as collect, \
                     patch.object(bot, "send_telegram_message", return_value=dict(status=status)):
                    self.assertEqual(bot.main(), 3)
                collect.assert_not_called()

    def test_finishing_today_does_not_create_duplicate_edition(self):
        self.freeze("2026-11-06")
        with patch.object(bot, "collect_all_articles") as collect, \
             patch.object(bot, "send_telegram_message", return_value=dict(status="sent", message_id=1, chat_id="test-chat")) as send:
            self.assertEqual(bot.main(), 5)
            self.assertEqual(bot.main(), 5)
        collect.assert_not_called()
        send.assert_called_once()


class FieldAndReceiptTests(unittest.TestCase):
    def test_4100_character_unbroken_title_is_rejected_before_review_or_format(self):
        a = article()
        raw = item(a)
        raw["titulo"] = "A" * 4100
        self.assertIsNone(bot.bind_item(raw, [a]))

    def test_invalid_long_field_is_replaced_and_substitute_is_reviewed(self):
        sources = [article(), article(2)]
        bad = item(sources[0])
        bad["titulo"] = "A" * 4100
        generation, reviewed_ids = [], []
        def call(instruction, payload, review=False):
            if review:
                reviewed_ids.extend(n["article_id"] for n in payload["rascunho"]["noticias"])
                return approval(payload["rascunho"], sources)
            if "vagas" in payload:
                generation.append(True)
                return dict(noticias=[bad] if len(generation) == 1 else [item(sources[1])])
            return dict(panorama="Decisão apoiada na matéria substituta.")
        with patch.object(bot, "call_gemini_json", side_effect=call):
            result = bot.build_reviewed_bulletin(sources, False)
        self.assertEqual([n["article_id"] for n in result["noticias"]], [sources[1]["id"]])
        self.assertNotIn(sources[0]["id"], reviewed_ids)
        self.assertIn(sources[1]["id"], reviewed_ids)
        self.assertTrue(bot.validate_publication(result, sources))
        parts = bot.format_bulletin_html(result, datetime.now(timezone.utc), False, [])
        for part in parts:
            self.assertLessEqual(len(part.encode("utf-16-le")) // 2, config.TELEGRAM_MAX_CHARS)
            ET.fromstring("<root>" + part + "</root>")

    def test_username_delivery_receipt_matches_numeric_id_and_username(self):
        response = Mock(status_code=200)
        response.json.return_value = dict(ok=True, result=dict(message_id=10,
            chat=dict(id=-100123, type="channel", username="news_channel")))
        with patch.object(bot, "TELEGRAM_CHAT_ID", "@news_channel"), \
             patch.object(bot, "TELEGRAM_BOT_TOKEN", "test-only"), \
             patch.object(bot.requests, "post", return_value=response) as post:
            receipt = bot.send_telegram_message("Texto revisado.")
        self.assertEqual(receipt["status"], "sent")
        self.assertEqual(receipt["chat_id"], "-100123")
        self.assertEqual(post.call_args.kwargs["json"]["chat_id"], "@news_channel")

    def test_mismatched_channel_username_remains_uncertain(self):
        response = Mock(status_code=200)
        response.json.return_value = dict(ok=True, result=dict(message_id=10,
            chat=dict(id=-100123, type="channel", username="different_channel")))
        with patch.object(bot, "TELEGRAM_CHAT_ID", "@news_channel"), \
             patch.object(bot, "TELEGRAM_BOT_TOKEN", "test-only"), \
             patch.object(bot.requests, "post", return_value=response):
            self.assertEqual(bot.send_telegram_message("Texto revisado.")["status"], "uncertain")

    def test_username_receipt_survives_checkpoint_without_changing_frozen_destination(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(config, "HISTORY_FILE", str(Path(tmp) / "history.json")), \
             patch.dict(os.environ, BOT_PERSIST_GIT="0", GITHUB_ACTIONS="false"):
            path = Path(tmp) / "outbox.json"
            store = DeliveryStore(path)
            edition = store.create("2026-11-05", [dict(text="Texto revisado.", article_ids=["one"])], "@news_channel", {})
            result = store.deliver(edition, lambda _: dict(status="sent", message_id=10,
                                  chat_id="-100123", chat_username="news_channel"))
            self.assertEqual(result, "complete")
            recovered = DeliveryStore(path).data["editions"][0]
            self.assertEqual(recovered["destination"], "@news_channel")
            self.assertEqual(recovered["parts"][0]["chat_id"], "-100123")


if __name__ == "__main__":
    unittest.main()
