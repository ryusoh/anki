import pathlib
import runpy
import sys
from typing import Any
from unittest.mock import MagicMock, patch

from graph.watch_and_update import main


def test_watch_keyboard_interrupt():
    with patch('graph.watch_and_update.argparse.ArgumentParser.parse_args') as mock_parse:
        mock_args: Any = mock_parse.return_value
        mock_args.auto_refresh = False

        with patch('graph.watch_and_update.get_current_size') as mock_size:
            mock_size.side_effect = [100, 200, KeyboardInterrupt()]

            with patch('graph.watch_and_update.increment'):
                with patch('graph.watch_and_update.time.sleep'):
                    main()


def test_main_exec():
    with patch('graph.watch_and_update.argparse.ArgumentParser.parse_args') as mock_parse:
        mock_args: Any = mock_parse.return_value
        mock_args.auto_refresh = False

        with patch('graph.watch_and_update.get_current_size') as mock_size:
            mock_size.side_effect = [100, 200, KeyboardInterrupt()]

            with patch('graph.watch_and_update.increment'):
                with patch('graph.watch_and_update.time.sleep'):
                    with patch('sys.exit'):
                        # run_path (not run_module): graph.watch_and_update is
                        # already imported at the top of this file, so run_module
                        # emits a RuntimeWarning about re-executing it. run_path
                        # runs the file fresh (identical execution) without that.
                        #
                        # run_path executes the script in a NEW module namespace, so
                        # the patch on graph.watch_and_update.increment above does NOT
                        # apply to the freshly-run __main__ — its increment() is the
                        # real one, which shells out via subprocess.run and mutates
                        # the tracked graph/.incremental_config.json. Patch
                        # subprocess.run at its source module (shared, so the fresh
                        # module sees it too) to keep this test side-effect-free.
                        with patch('subprocess.run'):
                            script = str(
                                pathlib.Path(__file__).resolve().parent.parent
                                / 'watch_and_update.py'
                            )
                            runpy.run_path(script, run_name='__main__')


def test_watch_auto_refresh():
    with patch('graph.watch_and_update.argparse.ArgumentParser.parse_args') as mock_parse:
        mock_args: Any = mock_parse.return_value
        mock_args.auto_refresh = True
        mock_args.max = 1000

        with patch('graph.watch_and_update.get_current_size') as mock_size:
            # 1. initialization: 100
            # 2. loop start current_size = 100
            # 3. get_current_size after increment = 150
            # 4. next loop: KeyboardInterrupt
            mock_size.side_effect = [100, 100, 150, KeyboardInterrupt()]

            # Mock `refresh_browser` inside the module
            with patch('graph.watch_and_update.refresh_browser') as mock_refresh:
                with patch('graph.watch_and_update.increment'):
                    with patch('graph.watch_and_update.time.sleep'):
                        main()
                        mock_refresh.assert_called()


def test_watch_exceeds_max():
    with patch('graph.watch_and_update.argparse.ArgumentParser.parse_args') as mock_parse:
        mock_args: Any = mock_parse.return_value
        mock_args.auto_refresh = False
        mock_args.max = 150

        with patch('graph.watch_and_update.get_current_size') as mock_size:
            mock_size.side_effect = [100, 200, KeyboardInterrupt()]

            with patch('graph.watch_and_update.increment'):
                with patch('graph.watch_and_update.refresh_browser'):
                    with patch('graph.watch_and_update.time.sleep'):
                        main()


def test_watch_changed_size_skip():
    with patch('graph.watch_and_update.argparse.ArgumentParser.parse_args') as mock_parse:
        mock_args: Any = mock_parse.return_value
        mock_args.auto_refresh = True
        mock_args.max = 1000

        with patch('graph.watch_and_update.get_current_size') as mock_size:
            # 1. init: 100
            # 2. loop 1: current = 200. Changed! Continues.
            # 3. loop 2: current = 200. Equal. Increments.
            # 4. get size after inc = 300
            # 5. loop 3: KeyboardInterrupt
            mock_size.side_effect = [100, 200, 200, 300, KeyboardInterrupt()]

            with patch('graph.watch_and_update.increment') as mock_inc:
                with patch('graph.watch_and_update.refresh_browser') as mock_refresh:
                    with patch('graph.watch_and_update.time.sleep'):
                        main()
                        mock_inc.assert_called_once()
                        mock_refresh.assert_called_once()


def test_refresh_browser():
    with patch('graph.watch_and_update.subprocess.run') as mock_run:
        from graph.watch_and_update import refresh_browser

        refresh_browser()
        mock_run.assert_called()


def test_refresh_browser_exception():
    with patch('graph.watch_and_update.subprocess.run') as mock_run:
        mock_run.side_effect = Exception("error")
        from graph.watch_and_update import refresh_browser

        refresh_browser()
        mock_run.assert_called()


def test_refresh_browser_apple_script():
    with patch('graph.watch_and_update.subprocess.run') as mock_run:
        from graph.watch_and_update import refresh_browser

        refresh_browser()
        # Verify the applescript gets run
        mock_run.assert_called_with(
            [
                'osascript',
                '-e',
                'tell application "Google Chrome" to tell active tab of window 1 to reload',
            ],
            capture_output=True,
        )


def test_watch_once_auto_refresh():
    with patch('graph.watch_and_update.argparse.ArgumentParser.parse_args') as mock_parse:
        mock_args: Any = mock_parse.return_value
        mock_args.once = True
        mock_args.auto_refresh = True

        with patch('graph.watch_and_update.increment') as mock_inc:
            with patch('graph.watch_and_update.refresh_browser') as mock_refresh:
                main()
                mock_inc.assert_called_once()
                mock_refresh.assert_called_once()


def test_auto_refresh_explicit():
    # specifically test line 103
    with patch('graph.watch_and_update.argparse.ArgumentParser.parse_args') as mock_parse:
        mock_args: Any = mock_parse.return_value
        mock_args.auto_refresh = True
        mock_args.max = None
        mock_args.once = False

        with patch('graph.watch_and_update.get_current_size') as mock_size:
            # 1. init: 100
            # 2. current: 100 -> increment() -> refresh_browser() -> last_size = 150
            # 3. exception
            mock_size.side_effect = [100, 100, 150, KeyboardInterrupt()]

            with patch('graph.watch_and_update.increment'):
                with patch('graph.watch_and_update.refresh_browser') as mock_refresh:
                    with patch('graph.watch_and_update.time.sleep'):
                        main()
                        mock_refresh.assert_called()
