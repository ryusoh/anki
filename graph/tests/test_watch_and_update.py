import unittest
from unittest.mock import patch, MagicMock
import subprocess
import io
import sys
from graph.watch_and_update import refresh_browser

class TestWatchAndUpdate(unittest.TestCase):
    @patch('subprocess.run')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_refresh_browser_success(self, mock_stdout, mock_run):
        # Mock successful subprocess run
        mock_run.return_value = MagicMock(returncode=0)

        refresh_browser()
        output = mock_stdout.getvalue()
        self.assertIn("🔄 Browser refreshed", output)

        # Verify subprocess.run was called with correct arguments
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        self.assertIn('osascript', args[0])
        self.assertIn('tell application "Google Chrome"', args[0][2])
        self.assertTrue(kwargs.get('capture_output'))

    @patch('subprocess.run')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_refresh_browser_error(self, mock_stdout, mock_run):
        # Mock subprocess run raising an exception
        error_message = "Command not found"
        mock_run.side_effect = Exception(error_message)

        refresh_browser()
        output = mock_stdout.getvalue()
        self.assertIn(f"⚠️  Could not refresh browser: {error_message}", output)

if __name__ == '__main__':
    unittest.main()
