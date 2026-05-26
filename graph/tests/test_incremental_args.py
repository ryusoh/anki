from unittest.mock import patch, MagicMock, mock_open
from graph.incremental_export import main
import sys
import pathlib

def test_status_missing_file():
    with patch('sys.argv', ['incremental_export.py', '--status']):
        with patch('graph.incremental_export.load_config', return_value={'sample_size': 100, 'increment': 10}):
            with patch.object(pathlib.Path, 'exists', return_value=True):
                with patch.object(pathlib.Path, 'stat') as mock_stat_method:
                    mock_stat = MagicMock()
                    mock_stat.st_size = 1048576
                    mock_stat_method.return_value = mock_stat
                    main()

def test_reset():
    with patch('sys.argv', ['incremental_export.py', '--reset']):
        with patch('graph.incremental_export.load_config', return_value={'sample_size': 500, 'increment': 10}):
            with patch('graph.incremental_export.save_config') as mock_save:
                with patch('graph.incremental_export.export_graph') as mock_export:
                    main()
                    mock_save.assert_called_with({'sample_size': 100, 'increment': 10})
                    mock_export.assert_called_with(100)

def test_size():
    with patch('sys.argv', ['incremental_export.py', '--size', '1000']):
        with patch('graph.incremental_export.load_config', return_value={'sample_size': 100, 'increment': 10}):
            with patch('graph.incremental_export.save_config') as mock_save:
                with patch('graph.incremental_export.export_graph') as mock_export:
                    main()
                    mock_save.assert_called_with({'sample_size': 1000, 'increment': 10})
                    mock_export.assert_called_with(1000)

def test_default_increments():
    with patch('sys.argv', ['incremental_export.py']):
        with patch('graph.incremental_export.load_config', return_value={'sample_size': 1000, 'increment': 10}):
            with patch('graph.incremental_export.save_config') as mock_save:
                with patch('graph.incremental_export.export_graph') as mock_export:
                    main()
                    mock_save.assert_called_with({'sample_size': 1100, 'increment': 100})
                    mock_export.assert_called_with(1100)

def test_large_increments():
    with patch('sys.argv', ['incremental_export.py']):
        with patch('graph.incremental_export.load_config', return_value={'sample_size': 50000, 'increment': 10}):
            with patch('graph.incremental_export.save_config') as mock_save:
                with patch('graph.incremental_export.export_graph') as mock_export:
                    main()
                    mock_save.assert_called_with({'sample_size': 55000, 'increment': 5000})

    with patch('sys.argv', ['incremental_export.py']):
        with patch('graph.incremental_export.load_config', return_value={'sample_size': 10000, 'increment': 10}):
            with patch('graph.incremental_export.save_config') as mock_save:
                with patch('graph.incremental_export.export_graph') as mock_export:
                    main()
                    mock_save.assert_called_with({'sample_size': 11000, 'increment': 1000})

    with patch('sys.argv', ['incremental_export.py']):
        with patch('graph.incremental_export.load_config', return_value={'sample_size': 5000, 'increment': 10}):
            with patch('graph.incremental_export.save_config') as mock_save:
                with patch('graph.incremental_export.export_graph') as mock_export:
                    main()
                    mock_save.assert_called_with({'sample_size': 5500, 'increment': 500})

def test_strip_html_none():
    from graph.incremental_export import strip_html
    assert strip_html(None) == ""

def test_main_exec():
    import runpy
    import builtins
    with patch('sys.argv', ['incremental_export.py', '--status']):
        with patch('graph.incremental_export.load_config', return_value={'sample_size': 100, 'increment': 10}):
            with patch.object(pathlib.Path, 'exists', return_value=True):
                with patch.object(pathlib.Path, 'stat') as mock_stat_method:
                    mock_stat = MagicMock()
                    mock_stat.st_size = 1048576
                    mock_stat_method.return_value = mock_stat
                    with patch('sys.exit') as mock_exit:
                        with patch.object(builtins, 'open', mock_open(read_data='{"sample_size": 100, "increment": 10}')):
                            runpy.run_module('graph.incremental_export', run_name='__main__')
