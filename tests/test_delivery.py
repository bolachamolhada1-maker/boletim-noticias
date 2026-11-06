import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

import config
import news_bot as bot


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "history.json"
        self.patch = patch.object(config, "HISTORY_FILE", str(self.path))
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_corrupt_history_is_never_silently_empty(self):
        self.path.write_text("{broken", encoding="utf-8")
        with self.assertRaises(ValueError): bot.load_history()

    def test_legacy_history_migrates_and_retention_is_dated(self):
        self.path.write_text(json.dumps(dict(sent_ids=["old", "older"],
            updated_at="2025-01-01T00:00:00+00:00")), encoding="utf-8")
        self.assertEqual(bot.load_history(), {"old", "older"})
        with patch.object(config, "HISTORY_MAX_ENTRIES", 2):
            bot.save_history({"old", "older", "new"})
        self.assertEqual(bot.load_history(), {"old", "new"})
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertIn("sent_at", data)
        self.assertGreater(data["sent_at"]["new"], data["sent_at"]["old"])

    def test_failed_atomic_replace_preserves_previous_history(self):
        from delivery_state import atomic_json
        self.path.write_text('{"sent_ids": ["previous"]}', encoding="utf-8")
        before = self.path.read_bytes()
        with patch("delivery_state.os.replace", side_effect=OSError("disk fault")):
            with self.assertRaises(OSError): atomic_json(self.path, dict(sent_ids=["new"]))
        self.assertEqual(self.path.read_bytes(), before)


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        import delivery_state as delivery
        self.delivery = delivery
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.json"
        self.history = Path(self.tmp.name) / "history.json"
        patch.dict(os.environ, BOT_PERSIST_GIT="0", GITHUB_ACTIONS="false").start()
        self.store = delivery.DeliveryStore(self.path)
        self.parts = [dict(text="Parte um", article_ids=["a"]),
                      dict(text="Parte dois", article_ids=["b"])]
        self.edition = self.store.create("2026-11-05", self.parts, "chat-test", {"frozen": True})
        patch.object(config, "HISTORY_FILE", str(self.history)).start()
        self.addCleanup(patch.stopall)

    def test_resume_frozen_edition_sends_only_pending_parts(self):
        sender = Mock(side_effect=[dict(status="sent", message_id=100, chat_id="chat-test"),
                                   dict(status="pending", error="ConnectTimeout")])
        self.assertEqual(self.store.deliver(self.edition, sender), "partial")
        restarted = self.delivery.DeliveryStore(self.path)
        edition = restarted.unfinished()
        self.assertEqual([p["text"] for p in edition["parts"]], ["Parte um", "Parte dois"])
        sender2 = Mock(return_value=dict(status="sent", message_id=101, chat_id="chat-test"))
        self.assertEqual(restarted.deliver(edition, sender2), "complete")
        self.assertEqual(sender2.call_args.args[0], "Parte dois")
        self.assertEqual(bot.load_history(), {"a", "b"})

    def test_uncertain_confirmation_is_not_automatically_retried(self):
        sender = Mock(return_value=dict(status="uncertain", error="ReadTimeout"))
        self.assertEqual(self.store.deliver(self.edition, sender), "partial")
        restarted = self.delivery.DeliveryStore(self.path)
        sender2 = Mock()
        self.assertEqual(restarted.deliver(restarted.unfinished(), sender2), "partial")
        sender2.assert_not_called()

    def test_crash_during_send_remains_uncertain_on_restart(self):
        def crash(_): raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt): self.store.deliver(self.edition, crash)
        restarted = self.delivery.DeliveryStore(self.path)
        sender = Mock()
        self.assertEqual(restarted.deliver(restarted.unfinished(), sender), "partial")
        sender.assert_not_called()

    def test_checkpoint_failure_prevents_send(self):
        self.store.checkpoint = Mock(side_effect=RuntimeError("push rejected"))
        sender = Mock()
        with self.assertRaises(RuntimeError): self.store.deliver(self.edition, sender)
        sender.assert_not_called()

    def test_corrupt_history_blocks_resume_before_any_part(self):
        self.history.write_text("{broken", encoding="utf-8")
        sender = Mock(return_value=dict(status="pending"))
        with self.assertRaises(ValueError): self.store.deliver(self.edition, sender)
        sender.assert_not_called()

    def test_durable_pre_send_state_survives_post_send_push_failure(self):
        durable = copy.deepcopy(self.store.data)
        def checkpoint():
            nonlocal durable
            if self.store.data["editions"][0]["parts"][0]["status"] == "sent":
                raise RuntimeError("push rejected after Telegram confirmation")
            durable = copy.deepcopy(self.store.data)
        self.store.checkpoint = checkpoint
        sender = Mock(return_value=dict(status="sent", message_id=100, chat_id="chat-test"))
        with self.assertRaises(RuntimeError): self.store.deliver(self.edition, sender)
        self.path.write_text(json.dumps(durable), encoding="utf-8")
        restarted = self.delivery.DeliveryStore(self.path)
        sender2 = Mock()
        self.assertEqual(restarted.deliver(restarted.unfinished(), sender2), "partial")
        sender2.assert_not_called()

    def test_frozen_content_tampering_blocks_resume(self):
        data = json.loads(self.path.read_text(encoding="utf-8"))
        data["editions"][0]["parts"][0]["text"] = "Outro texto"
        self.path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValueError): self.delivery.DeliveryStore(self.path)

    def test_item_split_across_parts_is_recorded_only_after_full_delivery(self):
        store = self.delivery.DeliveryStore(Path(self.tmp.name) / "split-state.json")
        edition = store.create("split", [dict(text="primeira metade", article_ids=["split"]),
                                        dict(text="segunda metade", article_ids=["split"])], "chat-test", {})
        sender = Mock(side_effect=[dict(status="sent", message_id=1, chat_id="chat-test"),
                                   dict(status="pending")])
        self.assertEqual(store.deliver(edition, sender), "partial")
        self.assertNotIn("split", bot.load_history())
        store.deliver(edition, lambda _: dict(status="sent", message_id=2, chat_id="chat-test"))
        self.assertIn("split", bot.load_history())

    def test_reconciled_last_receipt_finishes_edition_persistently(self):
        for i, part in enumerate(self.edition["parts"]):
            part.update(status="sent", message_id=i+1, chat_id="chat-test",
                        sent_at="2026-11-05T20:00:00+00:00")
        self.edition["status"] = "partial"
        self.store.checkpoint()
        sender = Mock()
        self.assertEqual(self.store.deliver(self.edition, sender), "complete")
        sender.assert_not_called()
        restarted = self.delivery.DeliveryStore(self.path)
        self.assertIsNone(restarted.unfinished())

    def test_telegram_429_is_pending_and_invalid_receipt_is_uncertain(self):
        responses = [Mock(status_code=429), Mock(status_code=200), Mock(status_code=503)]
        responses[0].json.return_value = dict(ok=False, error_code=429)
        responses[1].json.return_value = dict(ok=True, result=dict(message_id=1, chat=dict(id="wrong-chat")))
        responses[2].json.return_value = dict(ok=False)
        with patch.object(bot, "TELEGRAM_BOT_TOKEN", "test-only"), \
             patch.object(bot, "TELEGRAM_CHAT_ID", "chat-test"), \
             patch.object(bot.requests, "post", side_effect=responses):
            self.assertEqual(bot.send_telegram_message("Texto")["status"], "pending")
            self.assertEqual(bot.send_telegram_message("Texto")["status"], "uncertain")
            self.assertEqual(bot.send_telegram_message("Texto")["status"], "uncertain")

    def test_telegram_timeout_types_have_different_states(self):
        for error, expected in ((requests.ConnectTimeout(), "pending"),
                                (requests.ReadTimeout(), "uncertain"),
                                (requests.ConnectionError(), "uncertain")):
            with self.subTest(expected=expected), patch.object(bot.requests, "post", side_effect=error) as post, \
                 patch.object(bot, "TELEGRAM_BOT_TOKEN", "test-token"), \
                 patch.object(bot, "TELEGRAM_CHAT_ID", "chat-test"):
                self.assertEqual(bot.send_telegram_message("Texto")["status"], expected)
                self.assertEqual(post.call_count, 1)

    def test_preview_never_posts_or_creates_state(self):
        with patch.object(bot.requests, "post") as post:
            bot.send_telegram_message("Texto", preview=True)
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
