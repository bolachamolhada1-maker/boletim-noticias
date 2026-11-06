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

    def test_weekend_window_and_monday_recap_with_delivery_deduplication(self):
        from datetime import datetime, timezone, timedelta
        for day, hours in ((7, 24), (8, 24), (9, 72), (10, 24)):
            with self.subTest(day=day):
                self.history.write_text(json.dumps({"sent_ids": [self.sources[0]["id"]]}), encoding="utf-8")
                if self.outbox.exists():
                    self.outbox.unlink()
                fixed = datetime(2026, 11, day, 17, tzinfo=timezone(timedelta(hours=-3)))
                def reviewed(candidates, monday):
                    data = stamped(dict(panorama="Decisao oficial.", noticias=[bot.bind_item(item(candidates[0]), candidates)]), candidates)
                    data["shortages"] = dict(BR=3, MUNDO=3)
                    return data
                with patch.object(bot, "datetime") as clock, \
                     patch.object(bot, "collect_all_articles", return_value=(copy.deepcopy(self.sources), [])) as collect, \
                     patch.object(bot, "enrich_candidates", side_effect=lambda a: a), \
                     patch.object(bot, "build_reviewed_bulletin", side_effect=reviewed) as build, \
                     patch.object(bot, "send_telegram_message", return_value=dict(status="sent", message_id=1, chat_id="test-chat")) as send:
                    clock.now.return_value = fixed
                    result = bot.main()
                    collect.assert_called_once_with(hours)
                    if day == 9:
                        self.assertEqual(result, 5)
                        self.assertTrue(build.call_args.args[0][0]["previously_sent"])
                        text = "\n".join(c.args[0] for c in send.call_args_list)
                        self.assertIn("Retrospectiva", text)
                        self.assertIn("Recapitula", text)
                        sent_count = send.call_count
                        self.assertEqual(bot.main(), 5)
                        self.assertEqual(send.call_count, sent_count)
                        self.assertEqual(collect.call_count, 1)
                    else:
                        self.assertEqual(result, 2)
                        build.assert_not_called()
                        send.assert_not_called()

    def test_daily_cron_preserves_brasilia_time(self):
        workflow = Path(".github/workflows/news_bot.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "0 20 * * *"', workflow)
        self.assertNotIn('cron: "0 20 * * 1-5"', workflow)

    def test_recap_label_is_reviewed_and_old_evidence_versions_are_unchanged(self):
        from editorial import evidence_snapshot
        original = evidence_snapshot(self.sources[0])
        self.assertNotIn("previously_sent", original)
        unchanged = dict(self.sources[0], previously_sent=False)
        self.assertEqual(original, evidence_snapshot(unchanged))
        source = dict(self.sources[0], previously_sent=True)
        bound = bot.bind_item(item(source), [source])
        self.assertEqual(bound, bot.bind_item(bound, [source]))
        data = stamped(dict(panorama="Recapitulação.", noticias=[bound]), [source])
        self.assertTrue(bot.validate_publication(data, [source]))
        data["noticias"][0]["contexto"] = ""
        self.assertFalse(bot.validate_publication(data, [source]))

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
