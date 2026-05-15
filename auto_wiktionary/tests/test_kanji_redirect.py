import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import detect_kanji_redirect, parse_wiktionary_html, fetch_wiktionary_html

# Real HTML from ja.wiktionary for 血眼 (redirects to ちまなこ)
CHIMANAKO_REDIRECT_HTML = """
<html>
    <body>
        <section>
            <h2>日本語</h2>
            <section>
                <h3>和語の漢字表記</h3>
                <p><strong class="Jpan headword" lang="ja"><a href="./血#日本語" title="血">血</a><a href="./眼#日本語" title="眼">眼</a></strong> (ちまなこ)</p>
                <ol><li><b><a href="./ちまなこ" title="ちまなこ">ちまなこ</a></b>の漢字表記。</li></ol>
            </section>
        </section>
    </body>
</html>
"""

# Real HTML from ja.wiktionary for 出鱈目 (redirects to でたらめ)
DETARAME_REDIRECT_HTML = """
<html>
    <body>
        <section>
            <h2>日本語</h2>
            <section>
                <h3>和語の漢字表記</h3>
                <p><strong class="Jpan headword" lang="ja">出鱈目</strong> (でたらめ)</p>
                <ol><li><b><a href="./でたらめ" title="でたらめ">でたらめ</a></b>の漢字表記。</li></ol>
            </section>
        </section>
    </body>
</html>
"""

# Normal definition page (正確 / せいかく) - should NOT be detected as redirect
NORMAL_DEFINITION_HTML = """
<html>
    <body>
        <section>
            <h2>日本語</h2>
            <p><strong class="Jpan headword" lang="ja">正確</strong> (せいかく)</p>
            <ol>
                <li>accurate definition.</li>
            </ol>
        </section>
    </body>
</html>
"""

# Page with multiple definitions - should NOT be redirect
MULTI_DEFINITION_HTML = """
<html>
    <body>
        <section>
            <h2>日本語</h2>
            <p><strong>邂逅</strong>（かいこう）</p>
            <ol>
                <li>思いがけなく出会うこと。</li>
                <li>思いがけなく出会う。</li>
            </ol>
        </section>
    </body>
</html>
"""


def test_detect_kanji_redirect_chimanako():
    """血眼 should redirect to ちまなこ"""
    result = detect_kanji_redirect(CHIMANAKO_REDIRECT_HTML)
    assert result == "ちまなこ"


def test_detect_kanji_redirect_detarame():
    """出鱈目 should redirect to でたらめ"""
    result = detect_kanji_redirect(DETARAME_REDIRECT_HTML)
    assert result == "でたらめ"


def test_no_redirect_for_normal_definition():
    """Normal definition pages should return None"""
    result = detect_kanji_redirect(NORMAL_DEFINITION_HTML)
    assert result is None


def test_no_redirect_for_multi_definitions():
    """Pages with multiple definitions should return None"""
    result = detect_kanji_redirect(MULTI_DEFINITION_HTML)
    assert result is None


def test_no_redirect_for_empty_html():
    result = detect_kanji_redirect("")
    assert result is None


def test_no_redirect_for_none():
    result = detect_kanji_redirect(None)
    assert result is None


def test_no_redirect_for_error():
    result = detect_kanji_redirect("Error: 500")
    assert result is None


# Real definition HTML for ちまなこ (the target after redirect)
CHIMANAKO_REAL_HTML = """
<html>
    <body>
        <section>
            <h2>日本語</h2>
            <section>
                <h3>名詞</h3>
                <p><strong class="Jpan headword" lang="ja">ちまなこ</strong><span class="headword-kanji">【<b class="Jpan" lang="ja"><a href="./血眼#日本語" title="血眼">血眼</a></b>】</span></p>
                <ol>
                    <li>逆上などで血走った眼。</li>
                    <li>夢中になって奔走すること。</li>
                </ol>
            </section>
        </section>
    </body>
</html>
"""


def test_redirect_then_parse_gives_real_definition():
    """Simulates the full flow: detect redirect from 血眼 HTML, then parse the target HTML."""
    redirect = detect_kanji_redirect(CHIMANAKO_REDIRECT_HTML)
    assert redirect == "ちまなこ"

    # Parse the real definition page
    parsed = parse_wiktionary_html(CHIMANAKO_REAL_HTML, lang="ja")
    assert "逆上" in parsed
    assert "夢中" in parsed


@patch('utils.fetch_wiktionary_html')
def test_full_redirect_flow_with_mock_fetch(mock_fetch):
    """End-to-end: fetching 血眼 triggers redirect, then fetches ちまなこ."""
    mock_fetch.side_effect = lambda word, lang: {
        "血眼": CHIMANAKO_REDIRECT_HTML,
        "ちまなこ": CHIMANAKO_REAL_HTML,
    }.get(word, "")

    # Step 1: fetch the kanji word
    html = fetch_wiktionary_html("血眼", "ja")
    redirect = detect_kanji_redirect(html)
    assert redirect == "ちまなこ"

    # Step 2: fetch the redirect target
    html = fetch_wiktionary_html(redirect, "ja")
    assert detect_kanji_redirect(html) is None  # not another redirect

    parsed = parse_wiktionary_html(html, lang="ja")
    assert "逆上" in parsed
    assert "夢中" in parsed


# ---- 口下手 (くちべた) test fixtures ----

# Real HTML from ja.wiktionary for 口下手 (redirects to くちべた)
KUCHIBETA_REDIRECT_HTML = """
<html>
    <body>
        <section>
            <h2>日本語</h2>
            <section>
                <h3>和語の漢字表記</h3>
                <p><strong class="Jpan headword" lang="ja"><a href="./口#日本語" title="口">口</a><a href="./下#日本語" title="下">下</a><a href="./手#日本語" title="手">手</a></strong> (くちべた)</p>
                <ol><li><b><a href="./くちべた" title="くちべた">くちべた</a></b>の漢字表記。</li></ol>
            </section>
        </section>
    </body>
</html>
"""

# Real HTML from ja.wiktionary for くちべた (the target after redirect)
# Note: pronunciation uses 【】 brackets, not () parentheses
KUCHIBETA_REAL_HTML = """
<html>
    <body>
        <section>
            <h2>日本語</h2>
            <section>
                <h3>名詞</h3>
                <p><strong class="Jpan headword" lang="ja">くちべた</strong>【<b class="Jpan" lang="ja"><a href="./口下手#日本語" title="口下手">口下手</a></b>】</p>
                <ol>
                    <li>人に思ったことを伝えるのが下手なこと。</li>
                </ol>
            </section>
        </section>
    </body>
</html>
"""


def test_detect_kanji_redirect_kuchibeta():
    """口下手 should redirect to くちべた"""
    result = detect_kanji_redirect(KUCHIBETA_REDIRECT_HTML)
    assert result == "くちべた"


def test_kuchibeta_redirect_preserves_pronunciation():
    """After redirecting 口下手 → くちべた, the pronunciation くちべた must appear in parsed output."""
    redirect = detect_kanji_redirect(KUCHIBETA_REDIRECT_HTML)
    assert redirect == "くちべた"

    parsed = parse_wiktionary_html(KUCHIBETA_REAL_HTML, lang="ja")
    # The definition should be present
    assert "下手" in parsed
    # The pronunciation (reading) must be present — this is the bug
    assert "くちべた" in parsed
