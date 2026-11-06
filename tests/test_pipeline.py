import copy
import unittest
from unittest.mock import patch

import config
import news_bot as bot
from tests.test_editorial import article, item


def stamped(draft, sources):
    from tests.test_editorial import approval
    report = approval(draft, sources)
    result = copy.deepcopy(draft)
    result["approval"] = dict(items={r["article_id"]: r["version"] for r in report["revisoes"]},
        events={r["article_id"]: r["evento_id"] for r in report["revisoes"]},
        panorama=report["panorama_version"], conjunto=report["conjunto_version"],
        reviewed_at="2026-11-05T16:47:00-03:00")
    return result


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.sources = [article(i) for i in range(6)] + [
            article(20+i, "MUNDO", title=f"France election {i}") for i in range(5)]

    def test_invalid_draft_ids_are_excluded_from_replacement(self):
        sources = self.sources[:5]
        calls = []
        def generate(instruction, payload, **kwargs):
            calls.append(payload)
            if len(calls) == 1:
                invalid = item(sources[0])
                invalid["resumo_desenvolvido"] = "palavra " * 181
                return dict(noticias=[invalid])
            return dict(noticias=[item(a) for a in sources[1:]])
        with patch.object(bot, "call_gemini_json", side_effect=generate):
            first = bot.summarize_with_ai(sources, False)
        self.assertEqual(first["attempted_ids"], [sources[0]["id"]])
        self.assertEqual(first["invalid_ids"], [sources[0]["id"]])

    def test_unresolved_invalid_draft_is_technical_even_when_catalog_exhausted(self):
        sources = self.sources[:2]
        draft = dict(noticias=[item(sources[0])], attempted_ids=[a["id"] for a in sources], invalid_ids=[sources[1]["id"]])
        with patch.object(bot, "summarize_with_ai", return_value=draft), \
             patch.object(bot, "review_bulletin", side_effect=stamped), \
             patch.object(bot, "call_gemini_json", return_value={"panorama": "Decisao."}):
            self.assertIsNone(bot.build_reviewed_bulletin(sources, False))

    def test_model_receives_exact_evidence_word_budget(self):
        with patch.object(bot, "call_gemini_json", return_value=dict(noticias=[])) as call:
            bot.summarize_with_ai(self.sources, False)
        self.assertEqual(call.call_args.args[1]["limites_palavras"][self.sources[0]["id"]], 60)

    def test_replacement_is_reviewed_and_final_quota_is_4_plus_3(self):
        calls = []
        def generate(pool, monday, accepted=None, **kwargs):
            used = {n["article_id"] for n in accepted or []}
            return dict(panorama="", noticias=[item(a) for a in pool if a["id"] not in used])
        def review(draft, sources):
            calls.append(copy.deepcopy(draft))
            result = stamped(draft, sources)
            # Primeiro lote perde uma matéria BR; exige reposição e novo parecer.
            if len(calls) == 1:
                result["noticias"] = result["noticias"][1:]
                result["panorama"] = ""
            return result
        with patch.object(bot, "summarize_with_ai", side_effect=generate), \
             patch.object(bot, "review_bulletin", side_effect=review), \
             patch.object(bot, "call_gemini_json", return_value={"panorama": "Decisões no Brasil e na França."}):
            result = bot.build_reviewed_bulletin(self.sources, False)
        self.assertEqual(sum(n["pais"] == "BR" for n in result["noticias"]), 4)
        self.assertEqual(sum(n["pais"] == "MUNDO" for n in result["noticias"]), 3)
        self.assertGreaterEqual(len(calls), 3)
        self.assertTrue(bot.validate_publication(result, self.sources))

    def test_insufficiency_is_explicit_without_duplicate_fill(self):
        sources = self.sources[:2]
        with patch.object(bot, "summarize_with_ai", return_value=dict(panorama="", noticias=[item(a) for a in sources])), \
             patch.object(bot, "review_bulletin", side_effect=stamped), \
             patch.object(bot, "call_gemini_json", return_value={"panorama": "Duas decisões no Brasil."}):
            result = bot.build_reviewed_bulletin(sources, False)
        self.assertEqual(len(result["noticias"]), 2)
        self.assertEqual(result["shortages"], {"BR": 2, "MUNDO": 3})
        self.assertTrue(bot.validate_publication(result, sources))

    def test_technical_review_failure_blocks_all_content(self):
        with patch.object(bot, "summarize_with_ai", return_value=dict(panorama="", noticias=[item(self.sources[0])])), \
             patch.object(bot, "review_bulletin", return_value=None):
            self.assertIsNone(bot.build_reviewed_bulletin(self.sources, False))

    def test_over_quota_drafts_are_bounded_in_code(self):
        with patch.object(bot, "summarize_with_ai", return_value=dict(panorama="", noticias=[item(a) for a in self.sources])), \
             patch.object(bot, "review_bulletin", side_effect=stamped), \
             patch.object(bot, "call_gemini_json", return_value={"panorama": "Decisões no Brasil e na França."}):
            result = bot.build_reviewed_bulletin(self.sources, False)
        self.assertEqual(len(result["noticias"]), 7)

    def test_final_rejection_uses_remaining_replacement_budget(self):
        calls = []
        def generate(pool, monday, accepted=None, excluded_ids=None):
            return dict(panorama="", noticias=[item(a) for a in pool if a["id"] not in (excluded_ids or set())])
        def review(draft, sources):
            calls.append(copy.deepcopy(draft))
            if len(calls) == 2:  # primeira revisão com panorama elimina uma notícia
                return dict(panorama="", noticias=draft["noticias"][1:])
            return stamped(draft, sources)
        with patch.object(bot, "summarize_with_ai", side_effect=generate), \
             patch.object(bot, "review_bulletin", side_effect=review), \
             patch.object(bot, "call_gemini_json", return_value={"panorama": "Decisões no Brasil e na França."}):
            result = bot.build_reviewed_bulletin(self.sources, False)
        self.assertEqual(len(result["noticias"]), 7)
        self.assertEqual(result["shortages"], {"BR": 0, "MUNDO": 0})


if __name__ == "__main__":
    unittest.main()
