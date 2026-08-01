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
    expected = '<blockquote style="border-left: 4px solid #ccc; padding: 6px 12px; margin: 10px 0; background-color: rgba(150, 150, 150, 0.08);">This is a quote</blockquote>'
    assert convert_markdown_field(html) == expected


def test_blockquote_html_encoded():
    html = '&gt; This is an encoded quote'
    expected = '<blockquote style="border-left: 4px solid #ccc; padding: 6px 12px; margin: 10px 0; background-color: rgba(150, 150, 150, 0.08);">This is an encoded quote</blockquote>'
    assert convert_markdown_field(html) == expected


def test_blockquote_multiple_br():
    html = '> Line one<br>&gt; Line two'
    expected = '<blockquote style="border-left: 4px solid #ccc; padding: 6px 12px; margin: 10px 0; background-color: rgba(150, 150, 150, 0.08);">Line one<br>Line two</blockquote>'
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
    html = '#### Heading<br>' 'Some **bold** text<br>' '<br>' '- Item one<br>' '- Item two'
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
    assert (
        '<b>这让 GPU 的片上缓存资源分配更合理，局部性更好，从而让 Warp 切换延迟隐藏的效率更高。</b>'
        in result
    )

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
# Code Blocks
# ---------------------------------------------------------------------------


def test_code_block_cpp():
    """Verify that a code block wraps code correctly and protects it from inner markdown formatting."""
    html = (
        '```cpp<br>'
        '__global__ void kernel(const float* __restrict__ input, float* output) {<br>'
        '&nbsp;&nbsp;&nbsp; // 使用 __ldg() 从全局内存只读加载<br>'
        '&nbsp;&nbsp;&nbsp; float val = __ldg(input + threadIdx.x);<br>'
        '&nbsp;&nbsp;&nbsp; output[threadIdx.x] = val * val;<br>'
        '}<br>'
        '```'
    )
    expected = (
        '<pre style="background-color: #1e1e1e; color: #d4d4d4; padding: 12px 16px; border-radius: 6px; overflow-x: auto; font-family: SFMono-Regular, Consolas, Liberation Mono, Menlo, monospace; font-size: 0.85em; line-height: 1.5; margin: 10px 0;"><code class="language-cpp">__global__ void kernel(const float* __restrict__ input, float* output) {<br>'
        '&nbsp;&nbsp;&nbsp; // 使用 __ldg() 从全局内存只读加载<br>'
        '&nbsp;&nbsp;&nbsp; float val = __ldg(input + threadIdx.x);<br>'
        '&nbsp;&nbsp;&nbsp; output[threadIdx.x] = val * val;<br>'
        '}</code></pre>'
    )
    assert convert_markdown_field(html) == expected


def test_code_block_protects_asterisks():
    """Make sure * in a code block is not converted to italic/bold."""
    html = '```c<br>' 'int *ptr = &val;<br>' '```'
    expected = '<pre style="background-color: #1e1e1e; color: #d4d4d4; padding: 12px 16px; border-radius: 6px; overflow-x: auto; font-family: SFMono-Regular, Consolas, Liberation Mono, Menlo, monospace; font-size: 0.85em; line-height: 1.5; margin: 10px 0;"><code class="language-c">int *ptr = &val;</code></pre>'
    assert convert_markdown_field(html) == expected


def test_code_block_fence_glued_to_closing_tag():
    """Fence glued onto preceding block HTML with no <br> before it.

    Anki's paste sometimes closes a block tag (e.g. `</ul>`) right before an
    opening ``` fence instead of inserting <br> — mirrors the real Back field
    of the 'JNZ（Jump if Not Zero，非零则跳转）' note. `_parse_code_blocks`
    requires the fence to start the part, so without splitting the fence off
    the block passes through unconverted.
    """
    html = (
        '<ul><li><b>示例</b>：</li></ul>'
        '```assembly<br>'
        '&nbsp; MOV CX, 5<br>'
        '&nbsp; JNZ LOOP_START<br>'
        '```'
    )
    out = convert_markdown_field(html)
    assert '<pre style=' in out
    assert '<code class="language-assembly">' in out
    assert '&nbsp; MOV CX, 5' in out
    assert out.startswith('<ul><li><b>示例</b>：</li></ul>')
    assert '```' not in out


def test_code_block_in_leaf_div_lines():
    """Code block when Anki stored the field as one leaf <div> per line.

    Mirrors the real 'Example: Logging Sidecar' card back field, where the
    YAML fence and every code line were wrapped in `<div>...</div>` instead
    of separated by `<br>`.
    """
    html = (
        '<div>Intro paragraph<br></div>'
        '<div><br></div>'
        '<div>```yaml</div>'
        '<div>apiVersion: v1</div>'
        '<div>kind: Pod</div>'
        '<div>metadata:</div>'
        '<div>&nbsp; name: example-pod</div>'
        '<div>```</div>'
        '<div><br></div>'
        '<div>Outro text</div>'
    )
    out = convert_markdown_field(html)
    assert '<pre style=' in out
    assert '<code class="language-yaml">' in out
    assert 'apiVersion: v1' in out
    assert 'kind: Pod' in out
    assert '&nbsp; name: example-pod' in out
    assert '```' not in out


def test_leaf_div_run_with_list_and_code():
    """A leaf-<div> run can contain both a code block and list items."""
    html = (
        '<div>```python</div>'
        '<div>def f():</div>'
        '<div>&nbsp;    pass</div>'
        '<div>```</div>'
        '<div><br></div>'
        '<div>- First item</div>'
        '<div>- Second item</div>'
    )
    out = convert_markdown_field(html)
    assert '<pre style=' in out
    assert '<code class="language-python">' in out
    assert '<ul>' in out
    assert '<li>First item</li>' in out
    assert '<li>Second item</li>' in out
    assert '```' not in out


def test_plain_leaf_div_preserved():
    """Plain prose wrapped in leaf <div>s without markdown markers is unchanged."""
    html = '<div>Just plain prose</div><div>Another line</div>'
    assert convert_markdown_field(html) == html


def test_leaf_div_code_block_idempotent():
    """Converting a leaf-<div> code block twice yields the same result."""
    html = '<div>```python</div><div>print(1)</div><div>```</div>'
    first = convert_markdown_field(html)
    second = convert_markdown_field(first)
    assert first == second


# ---------------------------------------------------------------------------
# Markdown Tables
# ---------------------------------------------------------------------------


def test_simple_table():
    """Verify simple table parsing."""
    html = '| col1 | col2 |<br>' '|---|---|<br>' '| val1 | val2 |'
    expected = (
        '<table style="border-collapse: collapse;">'
        '<thead><tr>'
        '<th style="border: 1px solid #ccc; padding: 6px 10px; background-color: rgba(150, 150, 150, 0.1); font-weight: bold; ">col1</th>'
        '<th style="border: 1px solid #ccc; padding: 6px 10px; background-color: rgba(150, 150, 150, 0.1); font-weight: bold; ">col2</th>'
        '</tr></thead>'
        '<tbody><tr>'
        '<td style="border: 1px solid #ccc; padding: 6px 10px; ">val1</td>'
        '<td style="border: 1px solid #ccc; padding: 6px 10px; ">val2</td>'
        '</tr></tbody>'
        '</table>'
    )
    assert convert_markdown_field(html) == expected


def test_table_with_alignment_and_formatting():
    """Verify table parsing with alignment (left, center, right) and formatting inside cells."""
    html = (
        '| Feature | **Lanczos** | Bicubic |<br>'
        '|:---|:---:|---:|<br>'
        '| Sharpness | `Very High` | Medium |'
    )
    expected = (
        '<table style="border-collapse: collapse;">'
        '<thead><tr>'
        '<th style="border: 1px solid #ccc; padding: 6px 10px; background-color: rgba(150, 150, 150, 0.1); font-weight: bold; text-align: left;">Feature</th>'
        '<th style="border: 1px solid #ccc; padding: 6px 10px; background-color: rgba(150, 150, 150, 0.1); font-weight: bold; text-align: center;"><b>Lanczos</b></th>'
        '<th style="border: 1px solid #ccc; padding: 6px 10px; background-color: rgba(150, 150, 150, 0.1); font-weight: bold; text-align: right;">Bicubic</th>'
        '</tr></thead>'
        '<tbody><tr>'
        '<td style="border: 1px solid #ccc; padding: 6px 10px; text-align: left;">Sharpness</td>'
        '<td style="border: 1px solid #ccc; padding: 6px 10px; text-align: center;"><code>Very High</code></td>'
        '<td style="border: 1px solid #ccc; padding: 6px 10px; text-align: right;">Medium</td>'
        '</tr></tbody>'
        '</table>'
    )
    assert convert_markdown_field(html) == expected


def test_real_world_d2d_table():
    """Verify conversion of the table from the D2D card."""
    html = (
        '| 模式 | 物理介质 | 距离 | 关键特性 |<br>'
        '| :--- | :--- | :--- | :--- |<br>'
        '| **标准封装（Standard）** | 有机基板 | 约 25mm | 类似极短距的串行接口，常用于连接基于不同工艺或来自不同厂商的 Chiplet。 |<br>'
        '| **先进封装（Advanced）** | 硅中介层、桥接 | &lt; 2mm | **超高密度布线**（线宽/间距可达微米级），带宽密度极高，常用于 CPU、GPU 和 HBM 之间的紧耦合。 |'
    )
    expected = (
        '<table style="border-collapse: collapse;">'
        '<thead><tr>'
        '<th style="border: 1px solid #ccc; padding: 6px 10px; background-color: rgba(150, 150, 150, 0.1); font-weight: bold; text-align: left;">模式</th>'
        '<th style="border: 1px solid #ccc; padding: 6px 10px; background-color: rgba(150, 150, 150, 0.1); font-weight: bold; text-align: left;">物理介质</th>'
        '<th style="border: 1px solid #ccc; padding: 6px 10px; background-color: rgba(150, 150, 150, 0.1); font-weight: bold; text-align: left;">距离</th>'
        '<th style="border: 1px solid #ccc; padding: 6px 10px; background-color: rgba(150, 150, 150, 0.1); font-weight: bold; text-align: left;">关键特性</th>'
        '</tr></thead>'
        '<tbody>'
        '<tr>'
        '<td style="border: 1px solid #ccc; padding: 6px 10px; text-align: left;"><b>标准封装（Standard）</b></td>'
        '<td style="border: 1px solid #ccc; padding: 6px 10px; text-align: left;">有机基板</td>'
        '<td style="border: 1px solid #ccc; padding: 6px 10px; text-align: left;">约 25mm</td>'
        '<td style="border: 1px solid #ccc; padding: 6px 10px; text-align: left;">类似极短距的串行接口，常用于连接基于不同工艺或来自不同厂商的 Chiplet。</td>'
        '</tr>'
        '<tr>'
        '<td style="border: 1px solid #ccc; padding: 6px 10px; text-align: left;"><b>先进封装（Advanced）</b></td>'
        '<td style="border: 1px solid #ccc; padding: 6px 10px; text-align: left;">硅中介层、桥接</td>'
        '<td style="border: 1px solid #ccc; padding: 6px 10px; text-align: left;">&lt; 2mm</td>'
        '<td style="border: 1px solid #ccc; padding: 6px 10px; text-align: left;"><b>超高密度布线</b>（线宽/间距可达微米级），带宽密度极高，常用于 CPU、GPU 和 HBM 之间的紧耦合。</td>'
        '</tr>'
        '</tbody>'
        '</table>'
    )
    assert convert_markdown_field(html) == expected


def test_table_glued_to_preceding_list_no_br():
    """A table pasted right after a list: Anki opens a new <div> instead of
    inserting <br> before the header row, so the row's '|' starts partway
    through a text part rather than at its front. The table must still be
    recognized (see the UALink card investigation)."""
    html = (
        "<div><ul><li>\n<div>intro text</div></li></ul>"
        "<div>| col1 | col2 |<br>"
        "| --- | --- |<br>"
        "| a | b |<br></div></div>"
    )
    expected = (
        "<div><ul><li>\n<div>intro text</div></li></ul>"
        "<div>"
        '<table style="border-collapse: collapse;">'
        "<thead><tr>"
        '<th style="border: 1px solid #ccc; padding: 6px 10px; background-color: rgba(150, 150, 150, 0.1); font-weight: bold; ">col1</th>'
        '<th style="border: 1px solid #ccc; padding: 6px 10px; background-color: rgba(150, 150, 150, 0.1); font-weight: bold; ">col2</th>'
        "</tr></thead>"
        "<tbody><tr>"
        '<td style="border: 1px solid #ccc; padding: 6px 10px; ">a</td>'
        '<td style="border: 1px solid #ccc; padding: 6px 10px; ">b</td>'
        "</tr></tbody>"
        "</table>"
        "</div></div>"
    )
    assert convert_markdown_field(html) == expected


# ---------------------------------------------------------------------------
# Redundant Line Breaks Spacing
# ---------------------------------------------------------------------------


def test_no_redundant_br_after_heading():
    """Verify that a <br> immediately after a heading is removed since heading is block-level."""
    html = '#### Heading<br>Text'
    expected = '<h4>Heading</h4>Text'
    assert convert_markdown_field(html) == expected


def test_one_br_preserved_for_empty_line_after_heading():
    """Verify that if two <br>s exist (standard paragraph gap), they are removed next to block elements."""
    html = '#### Heading<br><br>Text'
    expected = '<h4>Heading</h4>Text'
    assert convert_markdown_field(html) == expected


def test_br_preserved_for_extra_empty_lines_after_heading():
    """Verify that if three <br>s exist, one extra <br> is kept to render an extra empty line."""
    html = '#### Heading<br><br><br>Text'
    expected = '<h4>Heading</h4><br>Text'
    assert convert_markdown_field(html) == expected


def test_no_redundant_br_before_heading():
    """Verify that a <br> immediately before a heading is removed."""
    html = 'Text<br>#### Heading'
    expected = 'Text<h4>Heading</h4>'
    assert convert_markdown_field(html) == expected


def test_no_redundant_br_around_table():
    """Verify that adjacent <br>s around a table are removed."""
    html = 'Text<br>| col |<br>|---|<br>| val |<br>More text'
    expected = 'Text<table style="border-collapse: collapse;"><thead><tr><th style="border: 1px solid #ccc; padding: 6px 10px; background-color: rgba(150, 150, 150, 0.1); font-weight: bold; ">col</th></tr></thead><tbody><tr><td style="border: 1px solid #ccc; padding: 6px 10px; ">val</td></tr></tbody></table>More text'
    assert convert_markdown_field(html) == expected


def test_no_redundant_br_around_code_block():
    """Verify that adjacent <br>s around a code block are removed."""
    html = 'Text<br>' '```cpp<br>' 'void f();<br>' '```<br>' 'More text'
    expected = 'Text<pre style="background-color: #1e1e1e; color: #d4d4d4; padding: 12px 16px; border-radius: 6px; overflow-x: auto; font-family: SFMono-Regular, Consolas, Liberation Mono, Menlo, monospace; font-size: 0.85em; line-height: 1.5; margin: 10px 0;"><code class="language-cpp">void f();</code></pre>More text'
    assert convert_markdown_field(html) == expected


def test_real_world_spacing_list_to_paragraph():
    """Verify that redundant spacing between list and normal paragraph is removed."""
    html = (
        '- 远端 GPU 收到 RDMA Read 请求，从其 HBM 读出数据并封装成 RDMA 响应，发回本地。<br>'
        '- 本地网卡收到响应后，不通过传统 DMA 写入显存的某个缓冲区，而是通过**缓存一致性互联**（如 NVLink-C2C、CXL 或 PCIe/CXL 的缓存注入机制）直接**写入 L2 Cache 中对应的 Cache Line**。<br>'
        '- 如果是多个合并的请求，网卡或 L2 控制器会将大 Message 拆分成独立的 Cache Line，逐一填入 L2 的对应 set/way，并更新一致性状态（通常为 Shared 或 Exclusive）。<br><br>'
        '这一步是“Cache 层面隐藏”的关键硬件支撑——数据就绪时，它已经躺在 SM 最快能拿到的 L2 里了（甚至有可能进一步推送到 L1）。'
    )
    expected = (
        '<ul>'
        '<li>远端 GPU 收到 RDMA Read 请求，从其 HBM 读出数据并封装成 RDMA 响应，发回本地。</li>'
        '<li>本地网卡收到响应后，不通过传统 DMA 写入显存的某个缓冲区，而是通过<b>缓存一致性互联</b>（如 NVLink-C2C、CXL 或 PCIe/CXL 的缓存注入机制）直接<b>写入 L2 Cache 中对应的 Cache Line</b>。</li>'
        '<li>如果是多个合并的请求，网卡或 L2 控制器会将大 Message 拆分成独立的 Cache Line，逐一填入 L2 的对应 set/way，并更新一致性状态（通常为 Shared 或 Exclusive）。</li>'
        '</ul>'
        '这一步是“Cache 层面隐藏”的关键硬件支撑——数据就绪时，它已经躺在 SM 最快能拿到的 L2 里了（甚至有可能进一步推送到 L1）。'
    )
    assert convert_markdown_field(html) == expected


def test_mathjax_with_other_markdown():
    """Verify that text around MathJax is still formatted correctly."""
    html = 'This is **bold** with \\(x^2\\) math and `code`.'
    expected = 'This is <b>bold</b> with \\(x^2\\) math and <code>code</code>.'
    assert convert_markdown_field(html) == expected


def test_real_world_sae_card():
    """Verify formatting on the real-world SAE card line containing both HTML tags, bold, and MathJax."""
    html = '<ul><li>**编码器**：将激活向量&nbsp;\\(\\mathbf{h} \\in \\mathbb{R}^d\\)&nbsp;映射到一个更高维。</li></ul>'
    expected = '<ul><li><b>编码器</b>：将激活向量&nbsp;\\(\\mathbf{h} \\in \\mathbb{R}^d\\)&nbsp;映射到一个更高维。</li></ul>'
    assert convert_markdown_field(html) == expected


def test_bold_mixed_with_existing_html_bold():
    """Verify that **bold** is converted even if <b>already bold</b> exists on the same line."""
    html = 'This is **bold** and <b>already bold</b>.'
    expected = 'This is <b>bold</b> and <b>already bold</b>.'
    assert convert_markdown_field(html) == expected


def test_real_world_sae_card_full_line():
    """Verify formatting on the full second line of the SAE card (contains list, MathJax, and b tags)."""
    html = (
        '<ul><li>**编码器**：将激活向量&nbsp;\\(\\mathbf{h} \\in \\mathbb{R}^d\\)&nbsp;映射到一个更高维。</li>'
        '<li>**解码器**：用这组潜在特征重建原始激活。</li></ul>'
        '训练完成后，解码器权重矩阵代表一个<b>特征方向</b>。'
    )
    expected = (
        '<ul><li><b>编码器</b>：将激活向量&nbsp;\\(\\mathbf{h} \\in \\mathbb{R}^d\\)&nbsp;映射到一个更高维。</li>'
        '<li><b>解码器</b>：用这组潜在特征重建原始激活。</li></ul>'
        '训练完成后，解码器权重矩阵代表一个<b>特征方向</b>。'
    )
    assert convert_markdown_field(html) == expected


def test_upgrade_existing_tables():
    """Verify that old unstyled HTML tables are upgraded to include borders, padding, and alignments."""
    html = (
        '<table>'
        '<thead><tr><th style="text-align: center;">col1</th><th>col2</th></tr></thead>'
        '<tbody><tr><td style="text-align: right;">val1</td><td>val2</td></tr></tbody>'
        '</table>'
    )
    expected = (
        '<table style="border-collapse: collapse;">'
        '<thead><tr>'
        '<th style="border: 1px solid #ccc; padding: 6px 10px; background-color: rgba(150, 150, 150, 0.1); font-weight: bold; text-align: center;">col1</th>'
        '<th style="border: 1px solid #ccc; padding: 6px 10px; background-color: rgba(150, 150, 150, 0.1); font-weight: bold; ">col2</th>'
        '</tr></thead>'
        '<tbody><tr>'
        '<td style="border: 1px solid #ccc; padding: 6px 10px; text-align: right;">val1</td>'
        '<td style="border: 1px solid #ccc; padding: 6px 10px; ">val2</td>'
        '</tr></tbody>'
        '</table>'
    )
    assert convert_markdown_field(html) == expected


def test_upgrade_existing_code_blocks():
    """Verify that old unstyled HTML pre/code elements are upgraded to the new dark-styled layout."""
    html = (
        'Some intro text<br>'
        '<pre><code class="language-cpp">__global__ void kernel() {}</code></pre>'
        '<br>Some outro text'
    )
    expected = (
        'Some intro text<br>'
        '<pre style="background-color: #1e1e1e; color: #d4d4d4; padding: 12px 16px; border-radius: 6px; overflow-x: auto; font-family: SFMono-Regular, Consolas, Liberation Mono, Menlo, monospace; font-size: 0.85em; line-height: 1.5; margin: 10px 0;"><code class="language-cpp">__global__ void kernel() {}</code></pre>'
        '<br>Some outro text'
    )
    assert convert_markdown_field(html) == expected


def test_upgrade_existing_blockquotes():
    """Verify that old unstyled HTML blockquote elements are upgraded to the new styled layout."""
    html = 'Intro text<br>' '<blockquote>This is an old quote</blockquote>' '<br>Outro text'
    expected = (
        'Intro text<br>'
        '<blockquote style="border-left: 4px solid #ccc; padding: 6px 12px; margin: 10px 0; background-color: rgba(150, 150, 150, 0.08);">This is an old quote</blockquote>'
        '<br>Outro text'
    )
    assert convert_markdown_field(html) == expected


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


def test_apply_converts_all_fields():
    """_apply_markdown processes every field, not just Front/Back."""
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
    editor.note.keys.return_value = ['Front', 'Back', 'Text', 'Extra']
    editor.note.fields = [
        '#### Front heading',
        '#### Back heading',
        '#### Text heading',
        '#### Extra heading',
    ]
    editor.addMode = False

    _apply_markdown(editor)

    assert editor.note.fields[0] == '<h4>Front heading</h4>'
    assert editor.note.fields[1] == '<h4>Back heading</h4>'
    assert editor.note.fields[2] == '<h4>Text heading</h4>'
    assert editor.note.fields[3] == '<h4>Extra heading</h4>'
    editor.note.flush.assert_called_once()
    editor.loadNoteKeepingFocus.assert_called_once()


def test_shortcut_registration():
    """on_editor_did_init_shortcuts appends Ctrl+M to the shortcuts list."""
    import sys
    from unittest.mock import MagicMock

    sys.modules['aqt'] = MagicMock()
    sys.modules['aqt.editor'] = MagicMock()
    sys.modules['aqt.gui_hooks'] = MagicMock()
    sys.modules['aqt.utils'] = MagicMock()

    import importlib

    import auto_markdown

    importlib.reload(auto_markdown)
    from auto_markdown import on_editor_did_init_shortcuts

    shortcuts = []
    editor = MagicMock()
    on_editor_did_init_shortcuts(shortcuts, editor)

    assert len(shortcuts) == 1
    assert shortcuts[0][0] == "Ctrl+M"
    assert callable(shortcuts[0][1])
