import copy
import json
import os
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock, patch

import config
import news_bot as bot
from delivery_state import DeliveryStore
from tests.test_editorial import article, item
from tests.test_pipeline import stamped


class MainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.history = Path(self.tmp.name) / "history.json"
        self.outbox = Path(self.tmp.name) / "delivery.json"
        patch.object(config, "HISTORY_FILE", str(self.history)).start()
        patch.object(config, "DELIVERY_STATE_FILE", str(self.outbox)).start()
        patch.dict(os.environ, BOT_PERSIST_GIT="0", GITHUB_ACTIONS="false").start()
        patch.object(bot, "execution_lock", side_effect=lambda: nullcontext()).start()
        patch.object(bot, "TELEGRAM_CHAT_ID", "test-chat").start()
        patch.object(bot, "TELEGRAM_BOT_TOKEN", "test-token").start()
        self.addCleanup(patch.stopall)
        self.sources = [article()]
        self.data = stamped(dict(panorama="Decisão oficial anunciada.", noticias=[item(self.sources[0])]), self.sources)
        self.data["shortages"] = dict(BR=3, MUNDO=3)

    def test_restart_resumes_frozen_content_without_rss_or_gemini(self):
        store = DeliveryStore()
        edition = store.create(bot.datetime.now(bot.timezone(bot.timedelta(hours=-3))).date().isoformat(), [dict(text="parte um", article_ids=[]),
                                                dict(text="parte dois", article_ids=[self.sources[0]["id"]])],
                               "test-chat", dict(bulletin=self.data, catalog=self.sources))
        sender = Mock(side_effect=[dict(status="sent", message_id=1, chat_id="test-chat"),
                                   dict(status="pending")])
        store.deliver(edition, sender)
        with patch.object(bot, "collect_all_articles") as collect, \
             patch.object(bot, "call_gemini_json") as gemini, \
             patch.object(bot, "send_telegram_message", return_value=dict(status="sent", message_id=2, chat_id="test-chat")) as send:
            self.assertEqual(bot.main(), 5)  # entrega completa, mas cotas insuficientes
        collect.assert_not_called()
        gemini.assert_not_called()
        send.assert_called_once_with("parte dois")

    def test_preview_never_mutates_production_files_or_sends(self):
        self.history.write_text('{"sent_ids": ["old"]}', encoding="utf-8")
        self.outbox.write_text("conteúdo de produção não deve nem ser carregado na prévia", encoding="utf-8")
        before = (self.history.read_bytes(), self.outbox.read_bytes())
        with patch.object(bot, "collect_all_articles", return_value=(self.sources, [])), \
             patch.object(bot, "enrich_candidates", side_effect=lambda a: a), \
             patch.object(bot, "build_reviewed_bulletin", return_value=self.data), \
             patch.object(bot.requests, "post") as post:
            self.assertEqual(bot.main(preview=True), 5)
        post.assert_not_called()
        self.assertEqual(before, (self.history.read_bytes(), self.outbox.read_bytes()))

    def test_empty_window_and_feed_failure_have_distinct_exit_codes(self):
        with patch.object(bot, "collect_all_articles", return_value=([], [dict(status="empty")])):
            self.assertEqual(bot.main(preview=True), 2)
        with patch.object(bot, "collect_all_articles", return_value=([], [dict(status="error")])):
            self.assertEqual(bot.main(preview=True), 4)

    def test_partial_delivery_returns_nonzero_and_keeps_receipt(self):
        with patch.object(bot, "collect_all_articles", return_value=(self.sources, [])), \
             patch.object(bot, "enrich_candidates", side_effect=lambda a: a), \
             patch.object(bot, "build_reviewed_bulletin", return_value=self.data), \
             patch.object(bot, "format_bulletin_html", return_value=[bot.format_bulletin_html(self.data, bot.datetime.now(bot.timezone.utc), False, [])[0]]), \
             patch.object(bot, "send_telegram_message", return_value=dict(status="uncertain", error="ReadTimeout")):
            self.assertEqual(bot.main(), 3)
        state = json.loads(self.outbox.read_text(encoding="utf-8"))
        self.assertEqual(state["editions"][0]["parts"][0]["status"], "uncertain")
        self.assertFalse(self.history.exists())


if __name__ == "__main__":
    unittest.main()
