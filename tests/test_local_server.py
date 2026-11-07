"""Tests for safe unattended local Git synchronization (no network)."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import local_server


class LocalServerTests(unittest.TestCase):
    def test_successful_git_sync(self):
        with patch.object(local_server.subprocess, "run", return_value=SimpleNamespace(returncode=0,stdout="Already up to date.",stderr="")) as run:
            local_server.sync_once()
        args,kw=run.call_args
        self.assertEqual(args[0], ["git", "pull", "--ff-only", "--no-rebase"])
        self.assertIsNone(local_server.STATUS["last_error"])
        self.assertIsNotNone(local_server.STATUS["last_success_utc"])

    def test_failed_git_sync_retains_checkout_and_logs(self):
        with TemporaryDirectory() as temp:
            with patch.object(local_server, "LOG", Path(temp)/"dashboard-sync.log"):
                with patch.object(local_server.subprocess, "run", return_value=SimpleNamespace(returncode=1,stdout="",stderr="Network unavailable")):
                    local_server.sync_once()
                self.assertIn("Network unavailable", local_server.STATUS["last_error"])
                self.assertIn("Network unavailable",(Path(temp)/"dashboard-sync.log").read_text())
if __name__=="__main__":
    unittest.main()
