"""Tests for auto_markdown.core — markdown-to-HTML field transform.

Fixtures are structure-faithful synthetics derived from the real LDG card
field dump (tools/dump_field.py '为什么 LDG 有助于延迟隐藏？').
"""

from __future__ import annotations

from auto_markdown.core import convert_markdown_field


# ---------------------------------------------------------------------------
# Headings
# ---------------------------------------------------------------------------

def test_h4_heading():
    html = '#### This is a heading'
    assert convert_markdown_field(html) == '<h4>This is a heading</h4>'


def test_h1_through_h6():
    for level in range(1, 7):
        prefix = '#' * level
        html = f'{prefix} Heading {level}'
        assert convert_markdown_field(html) == f'<h{level}>Heading {level}</h{level}>'


def test_heading_with_emoji_number():
    """Real pattern from the LDG card: #### ① description."""
    html = '#### ① 在本地访存时，它是"更智能"的加载'
    expected = '<h4>① 在本地访存时，它是"更智能"的加载</h4>'
    assert convert_markdown_field(html) == expected


def test_heading_not_converted_if_no_space():
    """####nospace should NOT become a heading (standard markdown requires space)."""
    html = '####nospace'
    assert convert_markdown_field(html) == '####nospace'


# ---------------------------------------------------------------------------
# Bold
# ---------------------------------------------------------------------------

def test_bold_double_asterisk():
    html = 'This is **bold** text'
    expected = 'This is <b>bold</b> text'
    assert convert_markdown_field(html) == expected


def test_bold_multiple():
    html = '**first** and **second**'
    expected = '<b>first</b> and <b>second</b>'
    assert convert_markdown_field(html) == expected


def test_bold_with_inline_code():
    """Real pattern: **`LDG` 让...** — bold wrapping code."""
    html = '**`LDG` 让"远端内存访问"在软件和指令层面看起来和本地全局加载没有任何区别**'
    result = convert_markdown_field(html)
    assert '<b>' in result
    assert '<code>LDG</code>' in result
    assert '</b>' in result


# ---------------------------------------------------------------------------
# Inline code
# ---------------------------------------------------------------------------

def test_inline_code():
    html = 'Use `LDG` for read-only data'
    expected = 'Use <code>LDG</code> for read-only data'
    assert convert_markdown_field(html) == expected


def test_inline_code_multiple():
    html = '`LDG` and `LD` instructions'
    expected = '<code>LDG</code> and <code>LD</code> instructions'
    assert convert_markdown_field(html) == expected


def test_inline_code_with_brackets():
    """Real pattern: `LDG [remote_addr]`."""
    html = '执行一条 `LDG [remote_addr]` 指令时'
    expected = '执行一条 <code>LDG [remote_addr]</code> 指令时'
    assert convert_markdown_field(html) == expected


# ---------------------------------------------------------------------------
# Unordered lists
# ---------------------------------------------------------------------------

def test_unordered_list_single():
    html = '- List item'
    expected = '<ul><li>List item</li></ul>'
    assert convert_markdown_field(html) == expected


def test_unordered_list_multiple_br():
    """Multiple list items separated by <br>."""
    html = '- First item<br>- Second item<br>- Third item'
    expected = '<ul><li>First item</li><li>Second item</li><li>Third item</li></ul>'
    assert convert_markdown_field(html) == expected


def test_unordered_list_with_inline_formatting():
    """Real pattern: list items containing bold and code."""
    html = '- 当 warp 执行一条 `LDG [remote_addr]` 指令时，LSU 会先查本地 TLB。'
    result = convert_markdown_field(html)
    assert '<ul><li>' in result
    assert '<code>LDG [remote_addr]</code>' in result
    assert '</li></ul>' in result


# ---------------------------------------------------------------------------
# Ordered lists
# ---------------------------------------------------------------------------

def test_ordered_list():
    html = '1. First<br>2. Second<br>3. Third'
    expected = '<ol><li>First</li><li>Second</li><li>Third</li></ol>'
    assert convert_markdown_field(html) == expected


# ---------------------------------------------------------------------------
# Horizontal rule
# ---------------------------------------------------------------------------

def test_horizontal_rule_dashes():
    html = '---'
    assert convert_markdown_field(html) == '<hr>'


def test_horizontal_rule_asterisks():
    html = '***'
    assert convert_markdown_field(html) == '<hr>'


# ---------------------------------------------------------------------------
# Blockquote
# ---------------------------------------------------------------------------

def test_blockquote():
    html = '> This is a quote'
    expected = '<blockquote>This is a quote</blockquote>'
    assert convert_markdown_field(html) == expected


def test_blockquote_multiple_br():
    html = '> Line one<br>> Line two'
    expected = '<blockquote>Line one<br>Line two</blockquote>'
    assert convert_markdown_field(html) == expected


# ---------------------------------------------------------------------------
# Mixed content
# ---------------------------------------------------------------------------

def test_heading_with_bold_and_code():
    """A heading line that also has bold and code."""
    html = '#### 使用 **`LDG`** 指令'
    result = convert_markdown_field(html)
    assert result.startswith('<h4>')
    assert '<b><code>LDG</code></b>' in result
    assert result.endswith('</h4>')


def test_multiline_mixed():
    """Heading, prose, list items across <br>."""
    html = (
        '#### Heading<br>'
        'Some **bold** text<br>'
        '<br>'
        '- Item one<br>'
        '- Item two'
    )
    result = convert_markdown_field(html)
    assert '<h4>Heading</h4>' in result
    assert '<b>bold</b>' in result
    assert '<ul><li>Item one</li><li>Item two</li></ul>' in result


# ---------------------------------------------------------------------------
# MathJax passthrough
# ---------------------------------------------------------------------------

def test_mathjax_inline_passthrough():
    r"""Don't mangle \(...\) MathJax expressions."""
    html = r'Energy \(E = mc^2\) is important'
    assert convert_markdown_field(html) == html


def test_mathjax_block_passthrough():
    r"""Don't mangle \[...\] MathJax expressions."""
    html = r'Block: \[E = mc^2\]'
    assert convert_markdown_field(html) == html


def test_anki_mathjax_tag_passthrough():
    html = '<anki-mathjax>x^2</anki-mathjax>'
    assert convert_markdown_field(html) == html


# ---------------------------------------------------------------------------
# Idempotency and no-op
# ---------------------------------------------------------------------------

def test_idempotent():
    """Running twice gives the same result."""
    html = '#### Heading<br>**bold** `code`<br>- item'
    first = convert_markdown_field(html)
    second = convert_markdown_field(first)
    assert first == second


def test_empty_string():
    assert convert_markdown_field('') == ''


def test_no_markdown():
    html = 'Just plain text with no markdown'
    assert convert_markdown_field(html) == html


def test_already_html_unchanged():
    """Already-converted HTML should pass through unchanged."""
    html = '<h4>Heading</h4><br><b>bold</b>'
    assert convert_markdown_field(html) == html


def test_plain_text_no_change():
    """Plain text with no markdown markers is byte-identical."""
    html = '为什么 LDG 有助于延迟隐藏？'
    assert convert_markdown_field(html) == html


# ---------------------------------------------------------------------------
# Real-world integration: the LDG card back field
# ---------------------------------------------------------------------------

def test_real_world_ldg_card():
    """Full back field from the real LDG card, verifying key conversions."""
    html = (
        '#### ① 在本地访存时，它是"更智能"的加载<br>'
        '对只读数据使用 `LDG`，意味着这部分访问不会挤占 L1 的宝贵空间。'
        'L1 可以安心地为频繁重用的临时变量（如求和结果、中间寄存器溢出）服务。'
        '**这让 GPU 的片上缓存资源分配更合理，局部性更好，从而让 Warp 切换延迟隐藏的效率更高。**<br>'
        '<br>'
        '#### ② 在远程 RDMA 访问中，它是"本地加载"的语义起点<br>'
        '在我之前的解释中，GPU 要能透明地把远程数据拉进来，核心思想就是复用本地的内存加载通路。'
        '**`LDG`（以及 `LD`）这类全局加载指令，恰好是这条通路的"触发点"**：<br>'
        '<br>'
        '- 当 warp 执行一条 `LDG [remote_addr]` 指令时，LSU（加载存储单元）会先查本地 TLB 和物理地址。<br>'
        '- 如果页表标记该地址属于远端 GPU 内存（通过 NVLink/UEC 等互联），那么这次加载就会被转成一次 RDMA 读取请求。<br>'
        '- 该 warp 会被换出，切换到其他 warp 继续计算。<br>'
        '- 等 RDMA 响应将数据直接注入 L2 缓存（甚至进一步推送到 L1/只读缓存）后，warp 被唤醒，仿佛只是经历了一次慢一点的缓存未命中。<br>'
        '<br>'
        '也就是说，**`LDG` 让"远端内存访问"在软件和指令层面看起来和本地全局加载没有任何区别**，'
        '只是延迟从几百纳秒（HBM）变成了几微秒（网络）。'
        '而 GPU 正是利用它海量 warp 的零开销切换，把这些多出来的微秒完全"吃"掉——'
        '这就是 Cache 层面隐藏 RDMA 延迟的根本。'
    )
    result = convert_markdown_field(html)

    # Headings converted
    assert '<h4>① 在本地访存时，它是"更智能"的加载</h4>' in result
    assert '<h4>② 在远程 RDMA 访问中，它是"本地加载"的语义起点</h4>' in result

    # Bold converted
    assert '<b>这让 GPU 的片上缓存资源分配更合理，局部性更好，从而让 Warp 切换延迟隐藏的效率更高。</b>' in result

    # Inline code converted
    assert '<code>LDG</code>' in result
    assert '<code>LDG [remote_addr]</code>' in result

    # List items wrapped
    assert '<ul>' in result
    assert '<li>' in result

    # No raw markdown markers left
    assert '####' not in result
    # (** may appear inside already-converted bold content check is complex,
    # just verify the key conversions happened)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_asterisk_not_list_in_prose():
    """A * in prose (not at line start) is not a list item."""
    html = 'This is 5 * 3 = 15'
    assert convert_markdown_field(html) == html


def test_hash_not_heading_mid_line():
    """A # mid-line is not a heading."""
    html = 'Issue #42 is important'
    assert convert_markdown_field(html) == html


def test_consecutive_blank_br_preserved():
    """<br><br> (blank line) passes through."""
    html = 'Line one<br><br>Line two'
    result = convert_markdown_field(html)
    assert '<br>' in result


def test_existing_html_tags_preserved():
    """Existing <b>, <code> etc. in the field are not double-wrapped."""
    html = 'Already <b>bold</b> and <code>code</code>'
    assert convert_markdown_field(html) == html


# ---------------------------------------------------------------------------
# Integration: button handler
# ---------------------------------------------------------------------------

def test_on_auto_markdown_calls_save_first():
    """Button handler must saveNow before reading fields."""
    import sys
    from unittest.mock import MagicMock

    sys.modules['aqt'] = MagicMock()
    sys.modules['aqt.editor'] = MagicMock()
    sys.modules['aqt.gui_hooks'] = MagicMock()
    sys.modules['aqt.utils'] = MagicMock()

    import importlib
    import auto_markdown
    importlib.reload(auto_markdown)
    from auto_markdown import on_auto_markdown

    editor = MagicMock()
    on_auto_markdown(editor)
    editor.saveNow.assert_called_once()


def test_apply_converts_both_fields():
    """_apply_markdown processes both Front and Back fields."""
    import sys
    from unittest.mock import MagicMock

    sys.modules['aqt'] = MagicMock()
    sys.modules['aqt.editor'] = MagicMock()
    sys.modules['aqt.gui_hooks'] = MagicMock()
    sys.modules['aqt.utils'] = MagicMock()

    import importlib
    import auto_markdown
    importlib.reload(auto_markdown)
    from auto_markdown import _apply_markdown

    editor = MagicMock()
    editor.note.keys.return_value = ['Front', 'Back']
    editor.note.fields = ['#### Front heading', '#### Back heading']
    editor.addMode = False

    _apply_markdown(editor)

    assert editor.note.fields[0] == '<h4>Front heading</h4>'
    assert editor.note.fields[1] == '<h4>Back heading</h4>'
    editor.note.flush.assert_called_once()
    editor.loadNoteKeepingFocus.assert_called_once()
