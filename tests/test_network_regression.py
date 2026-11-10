"""Hostile network metadata fixtures; never contact remote services."""
import json
import sys
import unittest
from unittest.mock import MagicMock, patch

import config
import web_access as web


class NetworkRegressionTests(unittest.TestCase):
    url = "https://g1.globo.com/politica/fixture.ghtml"

    def document(self, node):
        return '<script type="application/ld+json">' + json.dumps(node) + '</script>'

    def test_nonstring_body_preserves_rss_fallback(self):
        for body in (None, 7, False, [], {}):
            with self.subTest(body=body):
                content = self.document({"@type": "NewsArticle", "url": self.url, "articleBody": body})
                with patch.object(web, "bounded_get", return_value=(content.encode(), self.url, "text/html")):
                    result = web.enrich_candidates([dict(id="fixture", url=self.url, summary="Trecho RSS.", body="")])
                self.assertEqual(result[0]["body"], "")
                self.assertEqual(result[0]["evidence_level"], "excerpt")

    def test_restriction_traversal_work_grows_with_input_size(self):
        costs = []
        for depth in (8, 12):
            node = {"isAccessibleForFree": True}
            for _ in range(depth):
                node = {"hasPart": node}
            article = {"@type": "NewsArticle", "url": self.url, "articleBody": "Corpo público.", "hasPart": node}
            document = self.document(article)
            calls = []
            def profile(frame, event, arg):
                if event == "call" and frame.f_code.co_filename == web.__file__:
                    calls.append(1)
            previous = sys.getprofile()
            try:
                sys.setprofile(profile)
                body, _ = web.extract_public_body(document, self.url)
            finally:
                sys.setprofile(previous)
            self.assertEqual(body, "Corpo público.")
            costs.append(len(calls))
            node["hasPart"]["isAccessibleForFree"] = False
            self.assertEqual(web.extract_public_body(self.document(article), self.url)[0], "")
        self.assertLess(costs[1], costs[0] * 3)

    def test_deadline_stops_a_slow_response_body(self):
        elapsed = [0]
        def chunks(_size):
            elapsed[0] = 1
            yield b"a"
            elapsed[0] = config.NETWORK_BUDGET_SECONDS + 1
            yield b"b"
        response = MagicMock(status_code=200, headers={})
        response.iter_content.side_effect = chunks
        with patch.object(web.time, "monotonic", side_effect=lambda: elapsed[0]), \
             patch.object(web, "is_public_url", return_value=True), \
             patch.object(web.requests, "Session") as factory:
            factory.return_value.__enter__.return_value.get.return_value.__enter__.return_value = response
            with self.assertRaises(web.FetchError):
                web.bounded_get(self.url)

    def test_overdeep_json_metadata_is_ignored_without_crash(self):
        document = '<script type="application/ld+json">' + '[' * 1100 + '{}' + ']' * 1100 + '</script>'
        self.assertEqual(web.extract_public_body(document, self.url)[0], "")

    def test_configured_feeds_use_https(self):
        self.assertTrue(all(feed["url"].startswith("https://") for feed in config.RSS_FEEDS))

    def test_plain_http_and_redirect_downgrade_are_blocked_before_request(self):
        with patch.object(web, "is_public_url", return_value=True), patch.object(web.requests, "Session") as factory:
            session = factory.return_value.__enter__.return_value
            with self.assertRaises(web.FetchError):
                web.bounded_get(self.url.replace("https:", "http:"))
            session.get.assert_not_called()
            redirect = MagicMock(status_code=302, headers={"Location": self.url.replace("https:", "http:")})
            session.get.return_value.__enter__.return_value = redirect
            with self.assertRaises(web.FetchError):
                web.bounded_get(self.url)
            self.assertEqual(session.get.call_count, 1)

    def test_deadline_covers_redirects_and_empty_responses(self):
        for status in (200, 302):
            with self.subTest(status=status):
                elapsed = [0]
                response = MagicMock(status_code=status, headers={"Location": self.url})
                response.iter_content.return_value = iter(())
                def request(*args, **kwargs):
                    elapsed[0] = config.NETWORK_BUDGET_SECONDS + 1
                    return response
                with patch.object(web.time, "monotonic", side_effect=lambda: elapsed[0]), \
                     patch.object(web, "is_public_url", return_value=True), \
                     patch.object(web.requests, "Session") as factory:
                    session = factory.return_value.__enter__.return_value
                    response.__enter__.return_value = response
                    session.get.side_effect = request
                    with self.assertRaises(web.FetchError):
                        web.bounded_get(self.url)
                    self.assertEqual(session.get.call_count, 1)
