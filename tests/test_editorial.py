import copy
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import config
import news_bot as bot


def article(i=1, country="BR", source="G1", title=None):
    url = f"https://g1.globo.com/politica/{i}.ghtml"
    return dict(id=bot.article_id(url), url=url, source=source, country=country,
                title=title or f"Brasil: decisão oficial número {i}",
                summary=f"Autoridade anunciou a decisão {i} nesta quinta-feira.",
                published_at="2026-11-05T12:00:00+00:00", topics=["política"],
                evidence_level="excerpt", body="")


def item(a):
    return dict(article_id=a["id"], evidence_ids=[a["id"]], titulo=a["title"],
                pais="BR" if a["country"] == "BR" else "MUNDO", tema="Política",
                resumo_desenvolvido=a["summary"], contexto="",
                consequencias=None, repercussao=None,
                limitacao="Evidência limitada ao trecho RSS.", divergencias=None,
                fonte_nome=a["source"], fonte_url=a["url"])


def approval(draft, articles):
    """Simula somente a fronteira externa Gemini, usando IDs/versionamento reais."""
    return dict(
        conjunto_version=bot.bulletin_version(draft, articles),
        acontecimentos_distintos=True,
        panorama_ok=True, panorama_observacao=None,
        panorama_version=bot.panorama_version(draft),
        revisoes=[dict(article_id=n["article_id"],
                       version=bot.item_version(n, articles), status="aprovada",
                       motivo=None, correcao=None, evento_id=f"evento-{n['article_id']}",
                       duplicada_de=None, fonte_suspeita=False)
                  for n in draft["noticias"]])


class EditorialTests(unittest.TestCase):
    def setUp(self):
        self.articles = [article()]
        self.draft = dict(panorama="Autoridade anunciou decisão.",
                          noticias=[item(self.articles[0])])
        self.api = patch.object(bot, "GEMINI_API_KEY", "test-only").start()
        patch.object(bot.time, "sleep").start()
        self.addCleanup(patch.stopall)

    def review_response(self, response):
        with patch.object(bot.genai, "GenerativeModel") as model:
            model.return_value.generate_content.return_value.text = json.dumps(response)
            return bot.review_bulletin(self.draft, self.articles)

    def test_missing_specific_verdict_blocks_item(self):
        result = self.review_response(dict(panorama_ok=True, revisoes=[]))
        self.assertFalse(result and result.get("noticias"))

    def test_legacy_title_only_approval_cannot_release(self):
        response = dict(panorama_ok=True, revisoes=[dict(
            titulo=self.draft["noticias"][0]["titulo"], status="aprovada")])
        self.assertFalse(self.review_response(response))

    def test_invalid_status_and_empty_correction_block(self):
        for status in (None, "desconhecido", "precisa_correcao"):
            with self.subTest(status=status):
                response = dict(panorama_ok=True, revisoes=[dict(
                    titulo=self.draft["noticias"][0]["titulo"], status=status,
                    correcao=None)])
                self.assertFalse(self.review_response(response))

    def test_explicit_versioned_approval_and_panorama_release(self):
        with patch.object(bot, "call_gemini_json", side_effect=lambda *args, **kw:
                          approval(self.draft, self.articles)):
            result = bot.review_bulletin(self.draft, self.articles)
        self.assertTrue(bot.validate_publication(result, self.articles))
        result["noticias"][0]["contexto"] = "Informação posterior."
        self.assertFalse(bot.validate_publication(result, self.articles))

    def test_missing_duplicate_unknown_and_stale_verdicts_fail_closed(self):
        for mode in ("missing", "duplicate", "unknown", "stale", "bad_status",
                     "no_status", "bad_panorama", "panorama_observation", "wrong_set"):
            with self.subTest(mode=mode):
                response = approval(self.draft, self.articles)
                rev = response["revisoes"][0]
                if mode == "missing": response["revisoes"] = []
                if mode == "duplicate": response["revisoes"].append(copy.copy(rev))
                if mode == "unknown": rev["article_id"] = "unknown"
                if mode == "stale": rev["version"] = "old-version"
                if mode == "bad_status": rev["status"] = "talvez"
                if mode == "no_status": del rev["status"]
                if mode == "bad_panorama": response["panorama_ok"] = False
                if mode == "panorama_observation": response["panorama_observacao"] = "Erro factual."
                if mode == "wrong_set": response["conjunto_version"] = "old-set"
                with patch.object(bot, "call_gemini_json", return_value=response):
                    self.assertFalse(bot.review_bulletin(self.draft, self.articles))

    def test_corrections_cover_all_fields_and_require_new_review(self):
        corrected = copy.deepcopy(self.draft)
        corrected["noticias"][0].update(titulo="Título corrigido", contexto="Contexto corrigido",
            consequencias="Próximo passo oficial", repercussao="Reação atribuída")
        first = approval(self.draft, self.articles)
        first["revisoes"][0].update(status="precisa_correcao", motivo="Imprecisão",
                                     correcao=corrected["noticias"][0])
        with patch.object(bot, "call_gemini_json", side_effect=[first, approval(corrected, self.articles)]) as api:
            result = bot.review_bulletin(self.draft, self.articles)
        self.assertEqual(api.call_count, 2)
        self.assertEqual(result["noticias"][0]["contexto"], "Contexto corrigido")
        self.assertTrue(bot.validate_publication(result, self.articles))

    def test_correction_never_approved_after_timeout_or_exhaustion(self):
        response = approval(self.draft, self.articles)
        response["revisoes"][0].update(status="precisa_correcao", motivo="erro",
                                     correcao=copy.deepcopy(self.draft["noticias"][0]))
        for responses in ([response, None], [response] * 10):
            with patch.object(bot, "call_gemini_json", side_effect=responses):
                self.assertFalse(bot.review_bulletin(self.draft, self.articles))

    def test_url_of_another_allowed_article_is_rejected(self):
        other = article(2)
        n = item(self.articles[0])
        n["fonte_url"] = other["url"]
        self.assertIsNone(bot.bind_item(n, self.articles + [other]))
        n["article_id"] = "unknown"
        self.assertIsNone(bot.bind_item(n, self.articles + [other]))

    def test_duplicate_event_cannot_fill_quota(self):
        self.articles.append(article(2))
        self.draft["noticias"].append(item(self.articles[1]))
        response = approval(self.draft, self.articles)
        for rev in response["revisoes"]: rev["evento_id"] = "mesmo-acontecimento"
        with patch.object(bot, "call_gemini_json", return_value=response):
            self.assertFalse(bot.review_bulletin(self.draft, self.articles))

    def test_suspect_source_seeks_other_authorized_evidence_and_is_rereviewed(self):
        other = article(2, source="BBC News")
        other.update(url="https://www.bbc.com/portuguese/articles/confirmation",
                     summary="Outra fonte registra divergência sobre a decisão oficial.")
        other["id"] = bot.article_id(other["url"])
        self.articles.append(other)
        first = approval(self.draft, self.articles)
        first["revisoes"][0].update(status="rejeitada", fonte_suspeita=True,
                                     motivo="Possível erro na fonte principal.")
        corrected = copy.deepcopy(self.draft)
        corrected["noticias"][0]["evidence_ids"].append(other["id"])
        corrected["noticias"][0]["divergencias"] = "As fontes divergem; não há solução comprovada."
        confirmation = dict(item=corrected["noticias"][0], confirmacoes=[
            dict(article_id=self.articles[0]["id"], trecho=self.articles[0]["summary"]),
            dict(article_id=other["id"], trecho=other["summary"])])
        with patch.object(bot, "call_gemini_json", side_effect=[first, confirmation, approval(corrected, self.articles)]) as call:
            result = bot.review_bulletin(self.draft, self.articles)
        self.assertEqual(call.call_count, 3)
        self.assertTrue(bot.validate_publication(result, self.articles))

    def test_same_publisher_domain_alias_is_not_independent_confirmation(self):
        for i, url in enumerate(("https://www1.folha.uol.com.br/poder/one.shtml", "https://folha.com.br/poder/two.shtml")):
            a = article(i)
            a.update(url=url, id=bot.article_id(url), source="Folha de S.Paulo")
            if i == 0: self.articles = [a]
            else: self.articles.append(a)
        self.draft = dict(panorama="Decisão.", noticias=[item(self.articles[0])])
        first = approval(self.draft, self.articles)
        first["revisoes"][0].update(status="rejeitada", fonte_suspeita=True, motivo="Erro suspeito")
        corrected = copy.deepcopy(self.draft)
        corrected["noticias"][0].update(evidence_ids=[a["id"] for a in self.articles], divergencias="Há divergência.")
        confirmation = dict(item=corrected["noticias"][0], confirmacoes=[
            dict(article_id=a["id"], trecho=a["summary"]) for a in self.articles])
        with patch.object(bot, "call_gemini_json", side_effect=[first, confirmation, approval(corrected, self.articles)]):
            result = bot.review_bulletin(self.draft, self.articles)
        self.assertFalse(result and result["noticias"])

    def test_collection_deduplication_is_independent_of_feed_order(self):
        short, rich = article(), article()
        rich["summary"] += " Outra informação comprovada no trecho mais completo."
        feeds = [dict(name="a", url="https://g1.globo.com/a"), dict(name="b", url="https://g1.globo.com/b")]
        def fetch(feed, cutoff): return [short] if feed["name"] == "a" else [rich]
        with patch.object(bot, "fetch_feed", side_effect=fetch), patch.object(config, "RSS_FEEDS", feeds):
            forward, _ = bot.collect_all_articles(24)
        with patch.object(bot, "fetch_feed", side_effect=fetch), patch.object(config, "RSS_FEEDS", list(reversed(feeds))):
            backward, _ = bot.collect_all_articles(24)
        self.assertEqual(forward, backward)

    def test_short_lead_cannot_be_expanded_into_long_article(self):
        n = item(self.articles[0])
        n["resumo_desenvolvido"] = ("Contexto sem evidência suficiente. " * 30).strip()
        self.assertIsNone(bot.bind_item(n, self.articles))

    def test_shared_selection_balances_categories_and_sources(self):
        articles = [article(i) for i in range(40)] + [
            article(i, "MUNDO", "BBC News", f"France election {i}") for i in range(40, 55)]
        selected = bot.select_candidates(articles, limit=14)
        self.assertEqual(len(selected), 14)
        self.assertGreaterEqual(sum(a["country"] == "MUNDO" for a in selected), 6)
        self.assertEqual([a["id"] for a in selected],
                         [a["id"] for a in bot.select_candidates(list(reversed(articles)), limit=14)])
        scarce = bot.select_candidates(articles[:12] + articles[40:41], limit=10)
        self.assertEqual(len(scarce), 10)
        self.assertEqual(sum(a["country"] == "MUNDO" for a in scarce), 1)

    def test_selection_diversifies_editorial_sources_not_feed_names(self):
        articles = [article(i) for i in range(10)]
        bbc = article(30, title="Brasil: decisão do governo", source="BBC News Brasil")
        bbc["url"] = "https://www.bbc.com/portuguese/articles/decision"
        bbc["id"] = bot.article_id(bbc["url"])
        selected = bot.select_candidates(articles + [bbc], limit=3)
        self.assertIn(bbc["id"], [a["id"] for a in selected])

    def test_evidence_change_invalidates_previous_approval(self):
        with patch.object(bot, "call_gemini_json", return_value=approval(self.draft, self.articles)):
            result = bot.review_bulletin(self.draft, self.articles)
        self.articles[0]["summary"] = "A fonte foi modificada."
        self.assertFalse(bot.validate_publication(result, self.articles))

    def test_generation_and_review_receive_identical_evidence_catalog(self):
        calls = []
        def call(instruction, payload, review=False):
            calls.append(payload["catalogo"])
            if not review:
                return self.draft
            return approval(dict(panorama="", noticias=self.draft["noticias"]), self.articles)
        with patch.object(bot, "call_gemini_json", side_effect=call):
            draft = bot.summarize_with_ai(self.articles, False)
            bot.review_bulletin(draft, self.articles)
        self.assertEqual(calls[0], calls[1])

    def test_generation_never_reassigns_hallucinated_reference(self):
        for invalid in ("https://g1.globo.com/politica/inventada", "https://evil.example/story"):
            raw = copy.deepcopy(self.draft)
            raw["noticias"][0]["fonte_url"] = invalid
            with patch.object(bot, "call_gemini_json", return_value=raw):
                self.assertEqual(bot.summarize_with_ai(self.articles, False)["noticias"], [])

    def test_rejected_item_ids_are_explicitly_excluded_in_generation(self):
        other = article(2)
        self.articles.append(other)
        with patch.object(bot, "call_gemini_json", return_value=self.draft) as api:
            result = bot.summarize_with_ai(self.articles, False, excluded_ids={self.articles[0]["id"]})
        self.assertEqual(api.call_args.args[1]["eligible_ids"], [other["id"]])
        self.assertEqual(result["noticias"], [])

    def test_empty_intermediate_panorama_cannot_prevent_regeneration(self):
        self.draft["panorama"] = ""
        response = approval(self.draft, self.articles)
        response.update(panorama_ok=False, panorama_observacao="Panorama ainda não foi redigido.")
        with patch.object(bot, "call_gemini_json", return_value=response):
            result = bot.review_bulletin(self.draft, self.articles)
        self.assertIsNotNone(result)
        self.assertFalse(bot.validate_publication(result, self.articles))

    def test_mixed_feeds_use_subject_not_publisher(self):
        self.assertEqual(bot.classify_subject(article(title="Eleições na França mudam o parlamento")), "MUNDO")
        self.assertEqual(bot.classify_subject(article(country="MUNDO", title="STF decide caso no Brasil")), "BR")
        self.assertEqual(bot.classify_subject(article(title="Decisão é anunciada")), "MISTO")

    def test_preview_fallback_keeps_international_candidates(self):
        articles = [article(i) for i in range(40)] + [article(90, "MUNDO", title="France election")]
        with patch.object(bot, "load_history", return_value={a["id"] for a in articles}), \
             patch.object(bot, "collect_all_articles", return_value=(articles, [])), \
             patch.object(bot, "enrich_candidates", side_effect=lambda a: a), \
             patch.object(bot, "summarize_with_ai", return_value=None) as generate, \
             patch.object(bot.requests, "post") as post:
            bot.main(preview=True)
        self.assertIn(articles[-1]["id"], [a["id"] for a in generate.call_args.args[0]])
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
