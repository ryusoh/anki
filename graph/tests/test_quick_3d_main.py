from unittest.mock import mock_open, patch

from graph.quick_3d import main


def test_quick_3d_main():
    with (
        patch('builtins.open', mock_open()),
        patch('gzip.open', mock_open(read_data='[{"guid":"1","front":"a","tags":""}]')),
        patch('graph.quick_3d.print'),
    ):
        main()


def test_quick_3d_main_no_file():
    with patch('sys.exit') as mock_exit:
        mock_exit.side_effect = Exception("sys.exit called")
        with patch('gzip.open', side_effect=FileNotFoundError):
            try:
                main()
            except Exception as e:
                assert str(e) == "sys.exit called"
            mock_exit.assert_called_once_with(0)
