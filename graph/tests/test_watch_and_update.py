import unittest
from unittest.mock import patch, MagicMock
import subprocess
import io
import sys
from graph.watch_and_update import refresh_browser

class TestWatchAndUpdate(unittest.TestCase):
    @patch('graph.watch_and_update.CONFIG_FILE')
    @patch('json.load')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_get_current_size_exists(self, mock_open, mock_json_load, mock_config_file):
        from graph.watch_and_update import get_current_size
        mock_config_file.exists.return_value = True
        mock_json_load.return_value = {'sample_size': 200}

        size = get_current_size()
        self.assertEqual(size, 200)
        mock_json_load.assert_called_once()
        mock_open.assert_called_once()

    @patch('graph.watch_and_update.CONFIG_FILE')
    def test_get_current_size_default(self, mock_config_file):
        from graph.watch_and_update import get_current_size
        mock_config_file.exists.return_value = False

        size = get_current_size()
        self.assertEqual(size, 100)

    @patch('graph.watch_and_update.subprocess.run')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_increment_success(self, mock_stdout, mock_run):
        from graph.watch_and_update import increment
        mock_run.return_value = MagicMock(returncode=0, stdout="Success")

        increment()
        output = mock_stdout.getvalue()

        self.assertIn("Incrementing...", output)
        self.assertIn("Success", output)
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        self.assertIn('--next', args[0])
        self.assertTrue(kwargs.get('capture_output'))

    @patch('graph.watch_and_update.subprocess.run')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_increment_error(self, mock_stdout, mock_run):
        from graph.watch_and_update import increment
        mock_run.return_value = MagicMock(returncode=1, stderr="Error message")

        increment()
        output = mock_stdout.getvalue()

        self.assertIn("Incrementing...", output)
        self.assertIn("Error: Error message", output)
        mock_run.assert_called_once()

    @patch('graph.watch_and_update.increment')
    @patch('graph.watch_and_update.refresh_browser')
    @patch('sys.argv', ['watch_and_update.py', '--once', '--auto-refresh'])
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_once_auto_refresh(self, mock_stdout, mock_refresh_browser, mock_increment):
        from graph.watch_and_update import main
        main()

        mock_increment.assert_called_once()
        mock_refresh_browser.assert_called_once()

        output = mock_stdout.getvalue()
        self.assertIn("Watcher started", output)

    @patch('graph.watch_and_update.time.sleep')
    @patch('graph.watch_and_update.get_current_size')
    @patch('sys.argv', ['watch_and_update.py', '--max', '200'])
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_max_reached(self, mock_stdout, mock_get_current_size, mock_sleep):
        from graph.watch_and_update import main
        mock_get_current_size.side_effect = [100, 200]

        main()

        mock_sleep.assert_called_once_with(30)
        output = mock_stdout.getvalue()
        self.assertIn("Reached max size: 200", output)

    @patch('graph.watch_and_update.time.sleep')
    @patch('graph.watch_and_update.get_current_size')
    @patch('graph.watch_and_update.increment')
    @patch('sys.argv', ['watch_and_update.py', '--interval', '10'])
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_loop_increment(self, mock_stdout, mock_increment, mock_get_current_size, mock_sleep):
        from graph.watch_and_update import main
        # First call sets last_size = 100
        # Second call is in loop, returns 100 (same size) -> increment called
        # Third call raises KeyboardInterrupt to exit loop
        mock_get_current_size.side_effect = [100, 100, 100]
        mock_sleep.side_effect = [None, KeyboardInterrupt()]

        main()

        mock_increment.assert_called_once()
        output = mock_stdout.getvalue()
        self.assertIn("Watcher stopped", output)

    @patch('graph.watch_and_update.time.sleep')
    @patch('graph.watch_and_update.get_current_size')
    @patch('graph.watch_and_update.increment')
    @patch('sys.argv', ['watch_and_update.py', '--interval', '10'])
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_loop_size_changed(self, mock_stdout, mock_increment, mock_get_current_size, mock_sleep):
        from graph.watch_and_update import main
        # First call sets last_size = 100
        # Second call is in loop, returns 200 (changed size) -> skip increment
        # Third call raises KeyboardInterrupt to exit loop
        mock_get_current_size.side_effect = [100, 200, 200]
        mock_sleep.side_effect = [None, KeyboardInterrupt()]

        main()

        mock_increment.assert_not_called()
        output = mock_stdout.getvalue()
        self.assertIn("Size changed: 100 → 200", output)
        self.assertIn("Watcher stopped", output)

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

def test_missing_coverage_watch():
    import sys
    from unittest.mock import patch, MagicMock
    from graph.watch_and_update import main
    import builtins
    import io

    # 103, 111
    # Test --auto-refresh
    with patch("graph.watch_and_update.increment") as mock_increment, \
         patch("graph.watch_and_update.refresh_browser") as mock_refresh, \
         patch("graph.watch_and_update.get_current_size", side_effect=[100, 100, 100]), \
         patch("graph.watch_and_update.time.sleep", side_effect=[None, KeyboardInterrupt()]), \
         patch('sys.argv', ['watch_and_update.py', '--interval', '10', '--auto-refresh']):
        main()
        mock_refresh.assert_called_once()

    with patch("graph.watch_and_update.main") as mock_main:
         import runpy
         try:
             with patch("builtins.exit") as mock_exit:
                  mock_exit.side_effect = SystemExit(0)
                  runpy.run_path(__file__.replace('tests/test_watch_and_update.py', 'watch_and_update.py'), run_name="__main__")
         except SystemExit:
             pass
