import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import detect_kanji_redirect, parse_wiktionary_html, fetch_wiktionary_html, inject_redirect_pronunciation

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
    reading, all_readings = detect_kanji_redirect(CHIMANAKO_REDIRECT_HTML)
    assert reading == "ちまなこ"
    assert all_readings == ["ちまなこ"]


def test_detect_kanji_redirect_detarame():
    """出鱈目 should redirect to でたらめ"""
    reading, all_readings = detect_kanji_redirect(DETARAME_REDIRECT_HTML)
    assert reading == "でたらめ"
    assert all_readings == ["でたらめ"]


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
    reading, _ = detect_kanji_redirect(CHIMANAKO_REDIRECT_HTML)
    assert reading == "ちまなこ"

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
    reading, _ = detect_kanji_redirect(html)
    assert reading == "ちまなこ"

    # Step 2: fetch the redirect target
    html = fetch_wiktionary_html(reading, "ja")
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
    reading, all_readings = detect_kanji_redirect(KUCHIBETA_REDIRECT_HTML)
    assert reading == "くちべた"
    assert all_readings == ["くちべた"]


def test_kuchibeta_redirect_preserves_pronunciation():
    """After redirecting 口下手 → くちべた, the pronunciation くちべた must appear in parsed output."""
    reading, _ = detect_kanji_redirect(KUCHIBETA_REDIRECT_HTML)
    assert reading == "くちべた"

    parsed = parse_wiktionary_html(KUCHIBETA_REAL_HTML, lang="ja")
    # The definition should be present
    assert "下手" in parsed
    # The pronunciation (reading) must be present — this is the bug
    assert "くちべた" in parsed


# ---- 着く (つく / はく) multi-reading redirect test fixtures ----

# Real HTML from ja.wiktionary for 着く (redirects to both つく and はく)
TSUKU_REDIRECT_HTML = """
<html>
    <body>
        <section>
            <h2>日本語</h2>
            <section>
                <h3>和語の漢字表記</h3>
                <p><strong class="Jpan headword" lang="ja"><a href="./着#日本語" title="着">着</a>く</strong> (つく 又は はく)</p>
                <ol>
                    <li><b><a href="./つく" title="つく">つく</a></b>の漢字表記。</li>
                    <li><b><a href="./はく" title="はく">はく</a></b>の漢字表記。</li>
                </ol>
            </section>
        </section>
    </body>
</html>
"""

TSUKU_REAL_HTML = """
<html>
    <body>
        <section>
            <h2>日本語</h2>
            <section>
                <h3>動詞</h3>
                <p><strong class="Jpan headword" lang="ja">つく</strong>【<b class="Jpan" lang="ja"><a href="./着く#日本語" title="着く">着く</a></b>】</p>
                <ol>
                    <li>目的地に達する。到着する。</li>
                    <li>ある位置を占める。</li>
                </ol>
            </section>
        </section>
    </body>
</html>
"""


def test_detect_kanji_redirect_multi_reading_tsuku():
    """着く has two readings (つく, はく), both 漢字表記 — should redirect to first reading and return all readings."""
    reading, all_readings = detect_kanji_redirect(TSUKU_REDIRECT_HTML)
    assert reading == "つく"
    assert all_readings == ["つく", "はく"]


def test_no_redirect_when_mixed_li_content():
    """If some <li> items are 漢字表記 and some are real definitions, it's NOT a redirect."""
    mixed_html = """
    <html><body><section><h2>日本語</h2>
        <ol>
            <li><b><a href="./つく">つく</a></b>の漢字表記。</li>
            <li>目的地に達する。到着する。</li>
        </ol>
    </section></body></html>
    """
    result = detect_kanji_redirect(mixed_html)
    assert result is None


def test_inject_pronunciation_multi_reading():
    """inject_redirect_pronunciation should prepend all readings at the top when multiple exist."""
    parsed = '<ul><p><strong>つく</strong></p><li>目的地に達する。到着する。</li></ul>'
    result = inject_redirect_pronunciation(parsed, ["つく", "はく"])
    assert "つく" in result
    assert "はく" in result
    assert "目的地" in result
    # Pronunciation must be at the very start (right after <ul>)
    assert result.startswith("<ul><p>つく 又は はく</p>")


def test_inject_pronunciation_single_reading_noop_when_already_present():
    """inject_redirect_pronunciation should not change output when pronunciation already at the top."""
    parsed = '<ul><p><strong>ちまなこ</strong></p><li>逆上などで血走った眼。</li></ul>'
    result = inject_redirect_pronunciation(parsed, ["ちまなこ"])
    assert result == parsed


def test_inject_pronunciation_single_reading_prepends_when_missing():
    """付く regression: single-reading redirect must prepend pronunciation when target page has no leading <p>."""
    # The real つく page starts with <li>, not <p> — pronunciation is missing
    parsed = (
        '<ul>'
        '<li>自動詞:付く・点く・着く・就く</li>'
        '<p><strong>つく</strong></p>'
        '<li>別々のものが、隙間なく合わさること。付着する。</li>'
        '</ul>'
    )
    result = inject_redirect_pronunciation(parsed, ["つく"])
    # Must prepend pronunciation at the top
    assert result.startswith('<ul><p>つく</p>')
    # All original content preserved
    assert '自動詞:付く' in result
    assert '付着する' in result


def test_inject_pronunciation_multi_section_no_leading_p():
    """When parsed output starts with <li> (no leading <p>), pronunciation must be prepended.

    The real つく page has multiple <p> tags mid-content (one per verb section).
    inject_redirect_pronunciation must NOT replace one of those — it must prepend.
    """
    # Simulates the real つく page structure: starts with <li>, has <p> tags mid-content
    multi_section = (
        '<ul>'
        '<li>自動詞:付く・点く・着く・就く</li>'
        '<p><strong>つく</strong></p>'
        '<li>別々のものが、隙間なく合わさること。付着する。</li>'
        '<p><strong>つく</strong></p>'
        '<li>離れていたところから、目的地に移動しおえる。到着する。</li>'
        '<p><strong>つく</strong></p>'
        '<li>擬声語・擬態語に付いてある状態になってくる意を示す。</li>'
        '</ul>'
    )
    result = inject_redirect_pronunciation(multi_section, ["つく", "はく"])

    # 1. Pronunciation must be at the very start
    assert result.startswith("<ul><p>つく 又は はく</p>")

    # 2. All original <p> tags must survive (not be eaten by a greedy regex)
    import re
    original_p_count = len(re.findall(r'<p>', multi_section))
    result_p_count = len(re.findall(r'<p>', result))
    # +1 for the prepended pronunciation <p>
    assert result_p_count == original_p_count + 1, (
        f"Expected {original_p_count + 1} <p> tags, got {result_p_count}"
    )

    # 3. All original content must be preserved
    assert "自動詞:付く" in result
    assert "付着する" in result
    assert "目的地" in result
    assert "擬声語" in result

    # 4. No extra blank lines
    assert "\n\n" not in result


def test_inject_pronunciation_no_extra_blank_lines():
    """Ensure inject_redirect_pronunciation does not add any blank lines."""
    parsed = '<ul><li>some definition</li></ul>'
    result = inject_redirect_pronunciation(parsed, ["つく", "はく"])
    assert "\n\n" not in result


def test_full_redirect_flow_multi_reading():
    """Full flow: detect redirect from 着く, parse つく definition, inject both readings."""
    reading, all_readings = detect_kanji_redirect(TSUKU_REDIRECT_HTML)
    assert reading == "つく"
    assert all_readings == ["つく", "はく"]

    # Target page is not a redirect
    assert detect_kanji_redirect(TSUKU_REAL_HTML) is None

    parsed = parse_wiktionary_html(TSUKU_REAL_HTML, lang="ja")
    parsed = inject_redirect_pronunciation(parsed, all_readings)
    assert "目的地" in parsed
    assert "到着" in parsed
    # Both readings must be present in pronunciation
    assert "つく" in parsed
    assert "はく" in parsed
    # Pronunciation must be at the top
    assert parsed.startswith("<ul><p>つく 又は はく</p>")


def test_full_redirect_flow_single_reading_tsuku():
    """付く regression: single-reading redirect to つく must still show pronunciation at the top."""
    # 付く redirect page (single reading)
    TSUKU_SINGLE_REDIRECT_HTML = """
    <html>
        <body>
            <section>
                <h2>日本語</h2>
                <section>
                    <h3>和語の漢字表記</h3>
                    <p><strong class="Jpan headword" lang="ja"><a href="./付#日本語" title="付">付</a>く</strong> (つく)</p>
                    <ol>
                        <li><b><a href="./つく" title="つく">つく</a></b>の漢字表記。</li>
                    </ol>
                </section>
            </section>
        </body>
    </html>
    """

    reading, all_readings = detect_kanji_redirect(TSUKU_SINGLE_REDIRECT_HTML)
    assert reading == "つく"
    assert all_readings == ["つく"]

    # The real つく page has an overview section WITHOUT a preceding <p>,
    # followed by individual verb sections that DO have <p> tags.
    TSUKU_MULTI_SECTION_HTML = """
    <html>
        <body>
            <section>
                <h2>日本語</h2>
                <section>
                    <h3>動詞</h3>
                    <ol>
                        <li>自動詞:付く・点く・着く・就く
                            <ol>
                                <li>「離れていた種火が、隙間なく本体へ移る」→<b>点く</b></li>
                                <li>「離れていたところから、隙間なく近い場所へ移動する」→<b>着く</b></li>
                            </ol>
                        </li>
                    </ol>
                </section>
                <section>
                    <h3>動詞:付く</h3>
                    <p><strong class="Jpan headword" lang="ja">つく</strong>【<b class="Jpan" lang="ja"><a href="./付く#日本語" title="付く">付く</a></b>】</p>
                    <ol>
                        <li>別々のものが、隙間なく合わさること。付着する。</li>
                    </ol>
                </section>
                <section>
                    <h3>動詞:着く</h3>
                    <p><strong class="Jpan headword" lang="ja">つく</strong>【<b class="Jpan" lang="ja"><a href="./着く#日本語" title="着く">着く</a></b>】</p>
                    <ol>
                        <li>目的地に達する。到着する。</li>
                    </ol>
                </section>
            </section>
        </body>
    </html>
    """

    parsed = parse_wiktionary_html(TSUKU_MULTI_SECTION_HTML, lang="ja")
    parsed = inject_redirect_pronunciation(parsed, all_readings)
    # Pronunciation must be at the top
    assert parsed.startswith('<ul><p>つく</p>')
    assert "付着する" in parsed
    assert "目的地" in parsed
    assert "到着" in parsed


# ---- 落ちる (おちる) "参照" redirect test fixtures ----

# Real HTML from ja.wiktionary for 落ちる (uses "参照" instead of "の漢字表記。")
OCHIRU_REDIRECT_HTML = """
<html>
    <body>
        <section>
            <h2>日本語</h2>
            <section>
                <h3>和語の漢字表記</h3>
                <p><b><a href="./落" title="落">落</a>ちる</b>（おちる）</p>
                <ol><li><b><a href="./おちる" title="おちる">おちる</a></b>　参照</li></ol>
            </section>
        </section>
    </body>
</html>
"""

OCHIRU_REAL_HTML = """
<html>
    <body>
        <section>
            <h2>日本語</h2>
            <section>
                <h3>動詞</h3>
                <p><strong class="Jpan headword" lang="ja">おちる</strong>【<b class="Jpan" lang="ja"><a href="./落ちる#日本語" title="落ちる">落ちる</a></b>】</p>
                <ol>
                    <li>上から下へ移動する。落下する。</li>
                    <li>あるべきものがなくなる。脱落する。</li>
                </ol>
            </section>
        </section>
    </body>
</html>
"""


def test_detect_sanshou_redirect_ochiru():
    """落ちる uses '参照' pattern instead of 'の漢字表記。' — should still redirect to おちる."""
    result = detect_kanji_redirect(OCHIRU_REDIRECT_HTML)
    assert result is not None, "detect_kanji_redirect should detect '参照' redirects"
    reading, all_readings = result
    assert reading == "おちる"
    assert all_readings == ["おちる"]


def test_full_redirect_flow_sanshou_ochiru():
    """Full flow: 落ちる (参照 redirect) → fetch おちる → get real definition."""
    result = detect_kanji_redirect(OCHIRU_REDIRECT_HTML)
    assert result is not None
    reading, all_readings = result
    assert reading == "おちる"

    parsed = parse_wiktionary_html(OCHIRU_REAL_HTML, lang="ja")
    parsed = inject_redirect_pronunciation(parsed, all_readings)
    assert "落下" in parsed
    assert "脱落" in parsed
    assert "おちる" in parsed


# ---- 関脇 (せきわけ) corner-bracket 「」 redirect test fixtures ----

# Real HTML from ja.wiktionary for 関脇.
# Note: the reading is wrapped in 「」 corner brackets: 「せきわけ」の漢字表記。
SEKIWAKE_REDIRECT_HTML = """
<html>
    <body>
        <section>
            <h2>日本語</h2>
            <section>
                <h3>和語の漢字表記</h3>
                <p><b><a href="./関#日本語" title="関">関</a> <a href="./脇#日本語" title="脇">脇</a></b></p>
                <ol><li>「<a href="./せきわけ" title="せきわけ">せきわけ</a>」の漢字表記。</li></ol>
            </section>
        </section>
    </body>
</html>
"""

# Real HTML from ja.wiktionary for せきわけ (the redirect target).
SEKIWAKE_REAL_HTML = """
<html>
    <body>
        <section>
            <h2>日本語</h2>
            <section>
                <h3>名詞</h3>
                <p><strong class="Jpan headword" lang="ja">せきわけ</strong><span class="headword-kanji">【<b class="Jpan" lang="ja"><a href="./関脇#日本語" title="関脇">関脇</a></b>】</span></p>
                <ol>
                    <li>相撲の番付で、大関の下、小結の上の地位。</li>
                </ol>
            </section>
        </section>
    </body>
</html>
"""


def test_detect_kanji_redirect_sekiwake_strips_corner_brackets():
    """関脇 redirects to せきわけ. The reading is wrapped in 「」 corner brackets
    in the source ('「せきわけ」の漢字表記。'), which must be stripped so the
    follow-up fetch uses 'せきわけ' (not '「せきわけ」', which 404s)."""
    result = detect_kanji_redirect(SEKIWAKE_REDIRECT_HTML)
    assert result is not None
    reading, all_readings = result
    assert reading == "せきわけ"
    assert all_readings == ["せきわけ"]


def test_full_redirect_flow_sekiwake():
    """Full flow: 関脇 (「」 corner-bracket redirect) → fetch せきわけ → real definition."""
    result = detect_kanji_redirect(SEKIWAKE_REDIRECT_HTML)
    assert result is not None
    reading, all_readings = result
    assert reading == "せきわけ"

    parsed = parse_wiktionary_html(SEKIWAKE_REAL_HTML, lang="ja")
    parsed = inject_redirect_pronunciation(parsed, all_readings)
    assert "相撲" in parsed
    assert "大関" in parsed
    assert "せきわけ" in parsed


# ---- 天下り (あまくだり) "「」を参照。" redirect test fixtures ----

# Real HTML from ja.wiktionary for 天下り.
# Note: the redirect uses the pattern '「あまくだり」を参照。' — the reading is
# wrapped in 「」 corner brackets, joined with を, and followed by 参照 + 。
AMAKUDARI_REDIRECT_HTML = """
<html>
    <body>
        <section>
            <h2>日本語</h2>
            <section>
                <h3>和語の漢字表記</h3>
                <p><b><a href="./天#日本語" title="天">天</a><a href="./下#日本語" title="下">下</a>り</b></p>
                <ol><li>「<a href="./あまくだり" title="あまくだり">あまくだり</a>」を参照。</li></ol>
            </section>
        </section>
    </body>
</html>
"""

# Real HTML from ja.wiktionary for あまくだり (the redirect target).
AMAKUDARI_REAL_HTML = """
<html>
    <body>
        <section>
            <h2>日本語</h2>
            <section>
                <h3>名詞</h3>
                <p><strong class="Jpan headword" lang="ja">あまくだり</strong><span class="headword-kanji">【<b class="Jpan" lang="ja"><a href="./天下り#日本語" title="天下り">天下り</a></b>】</span></p>
                <ol>
                    <li>神仏が天界から地上に降りてくること。</li>
                    <li>退職した官僚が関連企業などの高い地位に就くこと。</li>
                </ol>
            </section>
        </section>
    </body>
</html>
"""


def test_detect_kanji_redirect_amakudari_wo_sanshou():
    """天下り redirects to あまくだり via the '「あまくだり」を参照。' pattern.
    The reading must be extracted (corner brackets stripped) so the follow-up
    fetch uses 'あまくだり', not the redirect notice itself."""
    result = detect_kanji_redirect(AMAKUDARI_REDIRECT_HTML)
    assert result is not None, "detect_kanji_redirect should detect '「…」を参照。' redirects"
    reading, all_readings = result
    assert reading == "あまくだり"
    assert all_readings == ["あまくだり"]


def test_full_redirect_flow_amakudari():
    """Full flow: 天下り ('「」を参照。' redirect) → fetch あまくだり → real definition.
    Must NOT show the bare '「あまくだり」を参照。' notice."""
    result = detect_kanji_redirect(AMAKUDARI_REDIRECT_HTML)
    assert result is not None
    reading, all_readings = result
    assert reading == "あまくだり"

    parsed = parse_wiktionary_html(AMAKUDARI_REAL_HTML, lang="ja")
    parsed = inject_redirect_pronunciation(parsed, all_readings)
    assert "を参照" not in parsed
    assert "天界" in parsed
    assert "官僚" in parsed
    assert "あまくだり" in parsed
