"""Executa a suíte com credenciais fictícias e HTTP externo bloqueado."""
import json
import os
import platform
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    os.chdir(ROOT)
    with patch("dotenv.load_dotenv", return_value=False), \
         patch.dict(os.environ, GEMINI_API_KEY="", TELEGRAM_BOT_TOKEN="", TELEGRAM_CHAT_ID="",
                    BOT_PERSIST_GIT="0", GITHUB_ACTIONS="false"), \
         patch("requests.sessions.Session.request", side_effect=AssertionError("HTTP externo proibido na suíte")):
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), top_level_dir=str(ROOT))
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = dict(checked_at=datetime.now(timezone.utc).isoformat(), python=platform.python_version(),
                  tests_run=result.testsRun, failures=[str(case) for case, trace in result.failures],
                  errors=[str(case) for case, trace in result.errors], skipped=len(result.skipped),
                  success=result.wasSuccessful(), external_http="blocked",
                  gemini="mocked", telegram="mocked", git="temporary local bare remotes")
    (ROOT / "docs" / "regression-results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
