import json
from unittest.mock import MagicMock, patch

from auto_image.utils import (
    _get_vqd_token,
    build_image_html,
    clean_html_text,
    download_image,
    fetch_image_results,
)


def _mock_response(data):
    mock = MagicMock()
    mock.read.return_value = data if isinstance(data, bytes) else data.encode('utf-8')
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


class TestCleanHtmlText:
    def test_empty_input(self):
        assert clean_html_text("") == ""
        assert clean_html_text(None) == ""

    def test_plain_text(self):
        assert clean_html_text("hello") == "hello"

    def test_strips_html_tags(self):
        assert clean_html_text("<b>hello</b> <i>world</i>") == "hello world"

    def test_strips_br_and_nbsp(self):
        assert clean_html_text("hello<br>world&nbsp;!") == "hello world !"

    def test_collapses_whitespace(self):
        assert clean_html_text("  hello   world  ") == "hello world"


class TestGetVqdToken:
    def test_extracts_vqd_from_html(self):
        fake_html = b'<html>some stuff vqd="abc123def" more stuff</html>'
        with patch(
            "auto_image.utils.urllib.request.urlopen", return_value=_mock_response(fake_html)
        ):
            assert _get_vqd_token("cat") == "abc123def"

    def test_returns_none_on_no_token(self):
        fake_html = b'<html>no token here</html>'
        with patch(
            "auto_image.utils.urllib.request.urlopen", return_value=_mock_response(fake_html)
        ):
            assert _get_vqd_token("cat") is None


class TestFetchImageResults:
    def test_empty_query_returns_empty_list(self):
        assert fetch_image_results("") == []
        assert fetch_image_results(None) == []

    def test_returns_thumbnail_urls(self):
        """fetch_image_results returns thumbnail URLs from results."""
        api_response = json.dumps(
            {
                "results": [
                    {
                        "image": "https://example.com/photo.jpg",
                        "thumbnail": "https://tse1.mm.bing.net/th?id=1",
                    },
                    {
                        "image": "https://example.com/photo2.jpg",
                        "thumbnail": "https://tse2.mm.bing.net/th?id=2",
                    },
                ]
            }
        )

        call_count = [0]

        def fake_urlopen(req, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return _mock_response(b'<html>vqd="token123"</html>')
            else:
                return _mock_response(api_response.encode('utf-8'))

        with patch("auto_image.utils.urllib.request.urlopen", side_effect=fake_urlopen):
            urls = fetch_image_results("cat")
            assert urls == ["https://tse1.mm.bing.net/th?id=1", "https://tse2.mm.bing.net/th?id=2"]
            assert call_count[0] == 2

    def test_returns_empty_list_on_no_results(self):
        api_response = json.dumps({"results": []})
        call_count = [0]

        def fake_urlopen(req, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return _mock_response(b'<html>vqd="token123"</html>')
            else:
                return _mock_response(api_response.encode('utf-8'))

        with patch("auto_image.utils.urllib.request.urlopen", side_effect=fake_urlopen):
            assert fetch_image_results("asjdflkajsdflkajsdf") == []

    def test_returns_empty_list_on_network_error(self):
        with (
            patch("auto_image.utils.urllib.request.urlopen", side_effect=Exception("timeout")),
            patch("auto_image.utils.logger.warning") as mock_warning,
        ):
            assert fetch_image_results("cat") == []
            mock_warning.assert_called_once()
            assert "Failed to fetch image results for query 'cat'" in mock_warning.call_args[0][0]

    def test_returns_empty_list_when_no_vqd_token(self):
        with patch(
            "auto_image.utils.urllib.request.urlopen",
            return_value=_mock_response(b'<html>nothing</html>'),
        ):
            assert fetch_image_results("cat") == []

    def test_filters_empty_thumbnails(self):
        api_response = json.dumps(
            {
                "results": [
                    {"image": "https://a.com/1.jpg", "thumbnail": ""},
                    {
                        "image": "https://b.com/2.jpg",
                        "thumbnail": "https://tse1.mm.bing.net/th?id=2",
                    },
                    {"image": "https://c.com/3.jpg"},
                ]
            }
        )
        call_count = [0]

        def fake_urlopen(req, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return _mock_response(b'<html>vqd="token123"</html>')
            else:
                return _mock_response(api_response.encode('utf-8'))

        with patch("auto_image.utils.urllib.request.urlopen", side_effect=fake_urlopen):
            urls = fetch_image_results("cat")
            assert urls == ["https://tse1.mm.bing.net/th?id=2"]


class TestDownloadImage:
    def test_returns_bytes_on_success(self):
        fake_bytes = b'\x89PNG\r\n\x1a\nfake'
        mock = _mock_response(fake_bytes)
        with patch("auto_image.utils.urllib.request.urlopen", return_value=mock):
            assert download_image("https://tse1.mm.bing.net/th?id=1") == fake_bytes

    def test_returns_none_on_error(self):
        with (
            patch("auto_image.utils.urllib.request.urlopen", side_effect=Exception("fail")),
            patch("auto_image.utils.logger.warning") as mock_warning,
        ):
            assert download_image("https://tse1.mm.bing.net/th?id=1") is None
            mock_warning.assert_called_once()
            assert (
                "Failed to download image from https://tse1.mm.bing.net/th?id=1"
                in mock_warning.call_args[0][0]
            )

    def test_returns_none_on_empty(self):
        assert download_image("") is None
        assert download_image(None) is None

    def test_returns_none_on_empty_body(self):
        mock = _mock_response(b'')
        with patch("auto_image.utils.urllib.request.urlopen", return_value=mock):
            assert download_image("https://tse1.mm.bing.net/th?id=1") is None


class TestBuildImageHtml:
    def test_builds_img_tag(self):
        html = build_image_html("https://example.com/photo.jpg")
        assert '<img src="https://example.com/photo.jpg"' in html
        assert 'max-width' in html

    def test_empty_url_returns_empty(self):
        assert build_image_html("") == ""
        assert build_image_html(None) == ""
