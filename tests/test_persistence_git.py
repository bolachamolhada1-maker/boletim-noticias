"""Integração Git real com remotes bare locais, sem tocar no repositório do usuário."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import config
import delivery_state as state


class GitPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.remote = self.root / "origin.git"
        self.checkout = self.root / "runner-a"
        self.run_git(self.root, "init", "--bare", str(self.remote))
        self.run_git(self.root, "clone", str(self.remote), str(self.checkout))
        self.run_git(self.checkout, "checkout", "-b", "main")
        (self.checkout / "history.json").write_text('{"sent_ids": []}', encoding="utf-8")
        self.run_git(self.checkout, "add", "history.json")
        self.commit(self.checkout, "initial")
        self.run_git(self.checkout, "push", "origin", "main")
        self.old_cwd = os.getcwd()
        os.chdir(self.checkout)
        self.addCleanup(os.chdir, self.old_cwd)
        patch.dict(os.environ, BOT_PERSIST_GIT="1", BOT_STATE_BRANCH="main").start()
        patch.object(config, "HISTORY_FILE", "history.json").start()
        patch.object(config, "DELIVERY_STATE_FILE", "delivery_state.json").start()
        self.addCleanup(patch.stopall)

    def run_git(self, cwd, *args, check=True):
        return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                              check=check, timeout=20)

    def commit(self, cwd, message):
        self.run_git(cwd, "-c", "user.name=Regression", "-c", "user.email=test@example.invalid",
                     "commit", "-m", message)

    def test_other_runner_recovers_confirmed_and_pending_parts(self):
        store = state.DeliveryStore()
        edition = store.create("2026-11-05", [dict(text="um", article_ids=["a"]),
                                                dict(text="dois", article_ids=["b"])], "chat", {})
        results = iter([dict(status="sent", message_id=1, chat_id="chat"), dict(status="pending")])
        self.assertEqual(store.deliver(edition, lambda _: next(results)), "partial")
        second = self.root / "runner-b"
        self.run_git(self.root, "clone", "--branch", "main", str(self.remote), str(second))
        os.chdir(second)
        recovered = state.DeliveryStore()
        sent = []
        def sender(text):
            sent.append(text)
            return dict(status="sent", message_id=2, chat_id="chat")
        self.assertEqual(recovered.deliver(recovered.unfinished(), sender), "complete")
        self.assertEqual(sent, ["dois"])
        self.assertEqual(state.load_history(), {"a", "b"})
        self.assertEqual(self.run_git(second, "rev-parse", "HEAD").stdout.strip(),
                         self.run_git(second, "ls-remote", "origin", "refs/heads/main").stdout.split()[0])

    def test_concurrent_remote_update_rejects_checkpoint_before_send(self):
        store = state.DeliveryStore()
        edition = store.create("2026-11-05", [dict(text="um", article_ids=["a"])], "chat", {})
        second = self.root / "runner-b"
        self.run_git(self.root, "clone", "--branch", "main", str(self.remote), str(second))
        (second / "other.txt").write_text("concorrência", encoding="utf-8")
        self.run_git(second, "add", "other.txt")
        self.commit(second, "concurrent update")
        self.run_git(second, "push", "origin", "main")
        sent = []
        with self.assertRaises(RuntimeError): store.deliver(edition, lambda text: sent.append(text))
        self.assertEqual(sent, [])


if __name__ == "__main__":
    unittest.main()
