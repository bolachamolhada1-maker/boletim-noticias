import copy
import json
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

import config
import news_bot as bot
import web_access as web
from tests.test_editorial import article, item
from tests.test_pipeline import stamped


class FormatTests(unittest.TestCase):
    def setUp(self):
        self.sources = [article()]
        self.data = dict(panorama="Decisão anunciada.", noticias=[item(self.sources[0])])
        self.data = stamped(self.data, self.sources)
        self.data["shortages"] = {"BR": 3, "MUNDO": 3}

    def test_actual_review_timestamp_is_used_instead_of_scheduled_time(self):
        parts = bot.format_bulletin_html(self.data, datetime(2026, 11, 5, 22, tzinfo=timezone.utc), False, [])
        text = "".join(parts)
        self.assertIn("16:47", text)
        self.assertNotIn("às 17h", text)

    def test_huge_fields_and_entities_fit_every_part_without_losing_content(self):
        n = self.data["noticias"][0]
        n["resumo_desenvolvido"] = "Texto & <conteúdo> 📰. " * 600
        parts = bot.format_bulletin_html(self.data, datetime.now(timezone.utc), False, [])
        self.assertGreater(len(parts), 2)
        for part in parts:
            self.assertLessEqual(len(part.encode("utf-16-le")) // 2, config.TELEGRAM_MAX_CHARS)
            ET.fromstring("<root>" + str(part) + "</root>")
            self.assertIn(n["article_id"], part.article_ids) if "Texto" in part else None
        combined = "".join(parts)
        self.assertEqual(combined.count("&lt;conteúdo&gt;"), 600)
        self.assertIn("Material comprovável insuficiente", combined)

    def test_unapproved_mutation_is_blocked_before_outbox(self):
        self.data["panorama"] = "Outra informação."
        with patch.object(bot, "collect_all_articles", return_value=(self.sources, [])), \
             patch.object(bot, "load_history", return_value=set()), \
             patch.object(bot, "enrich_candidates", side_effect=lambda x: x), \
             patch.object(bot, "build_reviewed_bulletin", return_value=self.data), \
             patch.object(bot.requests, "post") as post:
            self.assertEqual(bot.main(preview=True), 4)
        post.assert_not_called()


class NetworkTests(unittest.TestCase):
    def test_keyword_filter_does_not_confuse_golpe_with_gol(self):
        self.assertFalse(bot.contains_excluded_keyword("Polícia investiga golpe financeiro no Brasil"))
        self.assertTrue(bot.contains_excluded_keyword("Futebol: jogador marca gol no campeonato"))

    def test_transport_is_not_editorial_authorization(self):
        for url in ("https://feeds.a.dj.com/rss/RSSWorldNews.xml", "https://rss.dw.com/x", "https://pox.globo.com/rss/g1/"):
            self.assertFalse(bot.is_authorized_domain(url))
        self.assertTrue(bot.is_authorized_domain("https://www.wsj.com/world/story"))
        self.assertFalse(bot.is_authorized_domain("https://wsj.com.evil.org/story"))

    def test_paywall_metadata_prevents_embedded_body_extraction(self):
        text = '<script type="application/ld+json">' + json.dumps(dict(
            isAccessibleForFree=False, articleBody="Texto restrito que não deve ser usado.")) + '</script><article><p>Lead público.</p></article>'
        body, observed = web.extract_public_body(text)
        self.assertEqual(body, "")
        self.assertIn("restrição", observed)

    def test_public_body_extraction_excludes_navigation(self):
        body, _ = web.extract_public_body('<nav>Menu</nav><article><p>Fato público.</p><aside>Publicidade</aside></article>')
        self.assertEqual(body, "Fato público.")

    def test_dns_failure_is_not_treated_as_safe(self):
        with patch.object(web.socket, "getaddrinfo", side_effect=web.socket.gaierror()):
            self.assertFalse(bot.is_safe_url("https://g1.globo.com/story"))

    def test_redirect_destination_is_blocked_before_request(self):
        response = Mock(status_code=302, headers={"Location": "http://127.0.0.1/secret"})
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        with patch.object(web, "is_public_url", return_value=True), patch.object(web.requests, "Session") as session:
            session.return_value.__enter__.return_value.get.return_value = response
            with self.assertRaises(web.FetchError): web.bounded_get("https://g1.globo.com/rss", feed=True)
            self.assertEqual(session.return_value.__enter__.return_value.get.call_count, 1)

    def test_short_rss_is_labelled_and_title_only_cannot_be_expanded(self):
        a = article()
        a["summary"] = ""
        self.assertIsNone(bot.bind_item(item(a), [a]))
        a["summary"] = "Uma decisão foi anunciada."
        n = item(a)
        n["limitacao"] = None
        bound = bot.bind_item(n, [a])
        self.assertIn("trecho RSS", bound["limitacao"])


if __name__ == "__main__":
    unittest.main()
