import sys
import os
from unittest.mock import MagicMock, patch, call

# Mock aqt before import
sys.modules['aqt'] = MagicMock()
sys.modules['aqt.gui_hooks'] = MagicMock()
sys.modules['aqt.editor'] = MagicMock()
sys.modules['aqt.utils'] = MagicMock()
sys.modules['aqt.mw'] = MagicMock()

import auto_image
from auto_image import _apply_image, on_auto_image, _on_selection_result, _use_front_field, on_editor_did_init_buttons, _image_cache


def _make_editor(fields=None, field_names=None, add_mode=False):
    editor = MagicMock()
    editor.note = MagicMock()
    editor.note.keys.return_value = field_names or ["Front", "Back"]
    editor.note.fields = fields or ["", ""]
    editor.addMode = add_mode
    return editor


class TestApplyImage:
    def setup_method(self):
        _image_cache.clear()
        sys.modules['aqt.utils'].tooltip.reset_mock()

    def test_empty_text_shows_tooltip(self):
        editor = _make_editor()
        with patch("auto_image.clean_html_text", return_value=""):
            _apply_image(editor, "")
        sys.modules['aqt.utils'].tooltip.assert_called()

    def _std_patches(self, urls=None, img_html=None):
        """Context managers for standard _apply_image mocking."""
        urls = urls or ["https://tse1.mm.bing.net/th?id=1"]
        img_html = img_html or '<img src="auto_image_cat_0.jpg" style="max-width:300px;">'
        return (
            patch("auto_image.clean_html_text", return_value="cat"),
            patch("auto_image.fetch_image_results", return_value=urls),
            patch("auto_image.download_image", return_value=b'\x89PNG fake'),
            patch("auto_image.build_image_html", return_value=img_html),
            patch("auto_image._save_to_media", return_value="auto_image_cat_0.jpg"),
        )

    def test_no_back_field_shows_tooltip(self):
        editor = _make_editor(field_names=["Front", "Reading"])
        p = self._std_patches()
        with p[0], p[1], p[2], p[3], p[4]:
            _apply_image(editor, "cat")
        tooltip_calls = [str(c) for c in sys.modules['aqt.utils'].tooltip.call_args_list]
        assert any("Back" in c for c in tooltip_calls)

    def test_no_image_found_shows_tooltip(self):
        editor = _make_editor()
        with patch("auto_image.clean_html_text", return_value="asjdflk"), \
             patch("auto_image.fetch_image_results", return_value=[]):
            _apply_image(editor, "asjdflk")
        sys.modules['aqt.utils'].tooltip.assert_called()

    def test_appends_image_to_back_field_plain(self):
        editor = _make_editor(fields=["cat", "existing content"])
        img_html = '<img src="https://example.com/cat.jpg" style="max-width:300px;">'
        p = self._std_patches(img_html=img_html)
        with p[0], p[1], p[2], p[3], p[4]:
            _apply_image(editor, "cat")
        result = editor.note.fields[1]
        assert img_html in result
        assert result.startswith("existing content")
        assert "<br><img" not in result

    def test_appends_image_to_back_field_div_wrapped(self):
        editor = _make_editor(fields=["cat", "<div>existing content</div>"])
        img_html = '<img src="https://example.com/cat.jpg" style="max-width:300px;">'
        p = self._std_patches(img_html=img_html)
        with p[0], p[1], p[2], p[3], p[4]:
            _apply_image(editor, "cat")
        result = editor.note.fields[1]
        assert img_html in result
        assert "<br><img" not in result

    def test_appends_image_to_empty_back_field(self):
        editor = _make_editor(fields=["cat", ""])
        img_html = '<img src="https://example.com/cat.jpg" style="max-width:300px;">'
        p = self._std_patches(img_html=img_html)
        with p[0], p[1], p[2], p[3], p[4]:
            _apply_image(editor, "cat")
        assert 'class="auto-image"' in editor.note.fields[1]
        assert img_html in editor.note.fields[1]

    def test_flushes_note_in_edit_mode(self):
        editor = _make_editor(fields=["cat", ""], add_mode=False)
        p = self._std_patches()
        with p[0], p[1], p[2], p[3], p[4]:
            _apply_image(editor, "cat")
        editor.note.flush.assert_called_once()

    def test_does_not_flush_in_add_mode(self):
        editor = _make_editor(fields=["cat", ""], add_mode=True)
        p = self._std_patches()
        with p[0], p[1], p[2], p[3], p[4]:
            _apply_image(editor, "cat")
        editor.note.flush.assert_not_called()

    def test_none_note_returns_early(self):
        editor = MagicMock()
        editor.note = None
        p = self._std_patches()
        with p[0], p[1], p[2], p[3], p[4]:
            _apply_image(editor, "cat")


class TestCycleImages:
    def setup_method(self):
        _image_cache.clear()
        sys.modules['aqt.utils'].tooltip.reset_mock()

    def _patches(self, urls):
        return (
            patch("auto_image.clean_html_text", side_effect=lambda t: t),
            patch("auto_image.fetch_image_results", return_value=urls),
            patch("auto_image.download_image", return_value=b'\x89PNG fake'),
            patch("auto_image._save_to_media", side_effect=lambda data, q, i: f"auto_image_{q}_{i}.jpg"),
            patch("auto_image.build_image_html", side_effect=lambda u: f'<img src="{u}" style="max-width:300px;">'),
        )

    def test_second_click_replaces_with_next_image(self):
        urls = ["https://example.com/img1.jpg", "https://example.com/img2.jpg"]

        editor = _make_editor(fields=["cat", "some definition"])
        p = self._patches(urls)
        with p[0], p[1], p[2], p[3], p[4]:
            _apply_image(editor, "cat")
        assert "cat_0.jpg" in editor.note.fields[1]
        assert "some definition" in editor.note.fields[1]

        p = self._patches(urls)
        with p[0], p[1], p[2], p[3], p[4]:
            _apply_image(editor, "cat")
        result = editor.note.fields[1]
        assert "cat_1.jpg" in result
        assert "cat_0.jpg" not in result
        assert "some definition" in result

    def test_third_click_cycles_to_third_image(self):
        urls = ["https://example.com/1.jpg", "https://example.com/2.jpg", "https://example.com/3.jpg"]

        editor = _make_editor(fields=["cat", ""])
        def do_click():
            p = self._patches(urls)
            with p[0], p[1], p[2], p[3], p[4]:
                _apply_image(editor, "cat")

        do_click()
        assert "0.jpg" in editor.note.fields[1]
        do_click()
        assert "1.jpg" in editor.note.fields[1]
        assert "0.jpg" not in editor.note.fields[1]
        do_click()
        assert "2.jpg" in editor.note.fields[1]
        assert "1.jpg" not in editor.note.fields[1]

    def test_wraps_around_after_last_result(self):
        urls = ["https://example.com/a.jpg", "https://example.com/b.jpg"]

        editor = _make_editor(fields=["cat", ""])
        def do_click():
            p = self._patches(urls)
            with p[0], p[1], p[2], p[3], p[4]:
                _apply_image(editor, "cat")

        do_click()  # index 0
        do_click()  # index 1
        do_click()  # wraps to index 0
        assert "0.jpg" in editor.note.fields[1]
        assert "1.jpg" not in editor.note.fields[1]

    def test_different_queries_have_independent_caches(self):
        cat_urls = ["https://example.com/cat1.jpg", "https://example.com/cat2.jpg"]
        dog_urls = ["https://example.com/dog1.jpg", "https://example.com/dog2.jpg"]

        editor = _make_editor(fields=["cat", ""])
        p = self._patches(cat_urls)
        with p[0], p[1], p[2], p[3], p[4]:
            _apply_image(editor, "cat")
        assert "cat_0.jpg" in editor.note.fields[1]

        editor2 = _make_editor(fields=["dog", ""])
        p2 = self._patches(dog_urls)
        with p2[0], p2[1], p2[2], p2[3], p2[4]:
            _apply_image(editor2, "dog")
        assert "dog_0.jpg" in editor2.note.fields[1]

    def test_uses_cached_results_on_repeat_click(self):
        """Second click should NOT re-fetch from the API."""
        urls = ["https://example.com/1.jpg", "https://example.com/2.jpg"]
        editor = _make_editor(fields=["cat", ""])
        fetch_mock = MagicMock(return_value=urls)

        def do_click():
            with patch("auto_image.clean_html_text", return_value="cat"), \
                 patch("auto_image.fetch_image_results", fetch_mock), \
                 patch("auto_image.download_image", return_value=b'fake'), \
                 patch("auto_image._save_to_media", side_effect=lambda d, q, i: f"auto_image_{q}_{i}.jpg"), \
                 patch("auto_image.build_image_html", side_effect=lambda u: f'<img src="{u}" style="max-width:300px;">'):
                _apply_image(editor, "cat")

        do_click()
        do_click()
        # fetch_image_results should only be called once (first click)
        assert fetch_mock.call_count == 1

class TestSaveToMedia:
    def setup_method(self):
        _image_cache.clear()
        sys.modules['aqt.utils'].tooltip.reset_mock()

    def test_saves_image_and_uses_local_filename(self):
        """Image should be saved to media and referenced locally."""
        editor = _make_editor(fields=["cat", ""])
        save_mock = MagicMock(return_value="auto_image_cat_0.jpg")

        with patch("auto_image.clean_html_text", return_value="cat"), \
             patch("auto_image.fetch_image_results", return_value=["https://tse1.mm.bing.net/th?id=1"]), \
             patch("auto_image.download_image", return_value=b'\x89PNG fake') as dl_mock, \
             patch("auto_image._save_to_media", save_mock), \
             patch("auto_image.build_image_html", return_value='<img src="auto_image_cat_0.jpg">'):
            _apply_image(editor, "cat")

        dl_mock.assert_called_once_with("https://tse1.mm.bing.net/th?id=1")
        save_mock.assert_called_once_with(b'\x89PNG fake', "cat", 0)
        assert "auto_image_cat_0.jpg" in editor.note.fields[1]

    def test_skips_failed_download(self):
        """If download fails, skip to next URL."""
        editor = _make_editor(fields=["cat", ""])
        urls = ["https://tse1.mm.bing.net/th?id=bad", "https://tse2.mm.bing.net/th?id=good"]

        call_count = [0]
        def fake_dl(url):
            call_count[0] += 1
            if "bad" in url:
                return None
            return b'\x89PNG fake'

        with patch("auto_image.clean_html_text", return_value="cat"), \
             patch("auto_image.fetch_image_results", return_value=urls), \
             patch("auto_image.download_image", side_effect=fake_dl), \
             patch("auto_image._save_to_media", return_value="auto_image_cat_1.jpg"), \
             patch("auto_image.build_image_html", return_value='<img src="auto_image_cat_1.jpg">'):
            _apply_image(editor, "cat")
        assert "auto_image_cat_1.jpg" in editor.note.fields[1]

    def test_tooltip_when_all_downloads_fail(self):
        editor = _make_editor(fields=["cat", ""])
        with patch("auto_image.clean_html_text", return_value="cat"), \
             patch("auto_image.fetch_image_results", return_value=["https://a.com/1", "https://b.com/2"]), \
             patch("auto_image.download_image", return_value=None):
            _apply_image(editor, "cat")
        tooltip_calls = [str(c) for c in sys.modules['aqt.utils'].tooltip.call_args_list]
        assert any("image" in c.lower() for c in tooltip_calls)


class TestOnAutoImage:
    def test_none_note_returns_early(self):
        editor = MagicMock()
        editor.note = None
        on_auto_image(editor)
        editor.web.evalWithCallback.assert_not_called()

    def test_calls_eval_for_selection(self):
        editor = _make_editor()
        on_auto_image(editor)
        editor.web.evalWithCallback.assert_called_once()


class TestOnSelectionResult:
    def test_with_selection_uses_selection(self):
        editor = _make_editor()
        _on_selection_result(editor, "dog")
        editor.saveNow.assert_called_once()

    def test_without_selection_uses_front_field(self):
        editor = _make_editor()
        _on_selection_result(editor, "")
        editor.saveNow.assert_called_once()


class TestUseFrontField:
    def test_no_front_field_shows_tooltip(self):
        editor = _make_editor(field_names=["Question", "Answer"])
        _use_front_field(editor)
        sys.modules['aqt.utils'].tooltip.assert_called()

    def test_uses_front_field_content(self):
        editor = _make_editor(fields=["cat", ""], field_names=["Front", "Back"])
        with patch("auto_image._apply_image") as mock_apply:
            _use_front_field(editor)
            mock_apply.assert_called_once_with(editor, "cat")


class TestEditorButton:
    def test_registers_button(self):
        buttons = []
        editor = MagicMock()
        editor.addButton.return_value = "btn"
        on_editor_did_init_buttons(buttons, editor)
        assert "btn" in buttons
        editor.addButton.assert_called_once()
