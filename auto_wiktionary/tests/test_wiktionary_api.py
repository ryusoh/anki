import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import (
    fetch_wiktionary_html,
    format_candidates_html,
    get_wiktionary_candidates,
    parse_wiktionary_html,
)


def test_get_wiktionary_candidates():
    # 'applz' should return some suggestions like 'apple', 'apply'
    candidates = get_wiktionary_candidates("applz", "en")
    assert isinstance(candidates, list)
    assert len(candidates) > 0
    assert "apple" in candidates or "apply" in candidates

    # Nonsense word should return empty list
    empty_candidates = get_wiktionary_candidates("ajsfkldsjafkljsdaf", "en")
    assert isinstance(empty_candidates, list)
    assert len(empty_candidates) == 0


def test_format_candidates_html():
    candidates = ["apple", "apply", "application"]
    html = format_candidates_html("applz", candidates)
    assert "Did you mean" in html
    assert "<ul>" not in html
    assert "<li>" not in html
    assert "apple<br>" in html
    assert "application<br>" in html or html.endswith("application")

    empty_html = format_candidates_html("ajsfkldsjafkljsdaf", [])
    assert empty_html == ""


def test_fetch_wiktionary_not_found():
    res = fetch_wiktionary_html("ajsfkldsjafkljsdaf", "en")
    assert res == ""


def test_parse_wiktionary_html_jazz_dot():
    # A simple mock html reflecting what wiktionary might return
    mock_html = """
    <html>
        <body>
            <p><strong><a href="./jazz">jazz</a> <a href="./dot">dot</a></strong> (<i>plural</i> <b><a href="./jazz_dots">jazz dots</a></b>)</p>
            <ol>
                <li>A <a href="/wiki/soul_patch">soul patch</a>.
                    <ul>
                        <li><span class="mw-editsection">edit</span>Example sentence here.</li>
                    </ul>
                </li>
            </ol>
        </body>
    </html>
    """
    parsed = parse_wiktionary_html(mock_html)
    assert "<i>plural</i> <b>jazz dots</b>" in parsed
    assert "<strong>" not in parsed
    assert "<a " not in parsed  # links unwrapped
    assert "Example sentence here" in parsed
    assert "edit" not in parsed  # editsection removed


def test_parse_wiktionary_html_seikaku():
    mock_html = """
    <html>
        <body>
            <section>
                <h2>日本語</h2>
                <p id="mwCQ"><strong about="#mwt5" class="Jpan headword" data-mw='{"parts":[{"template":{"target":{"wt":"ja-noun","href":"./テンプレート:ja-noun"},"params":{"1":{"wt":"[[せいかく]]"}},"i":0}}]}' id="mwCg" lang="ja" typeof="mw:Transclusion"><a href="./正#日本語" rel="mw:WikiLink" title="正">正</a><a href="./確#日本語" rel="mw:WikiLink" title="確">確</a></strong><span about="#mwt5"> (</span><span about="#mwt5" class="headword-tr manual-tr tr" dir="ltr"><a href="./せいかく" rel="mw:WikiLink" title="せいかく">せいかく</a></span><span about="#mwt5">)</span><link about="#mwt5" href="./カテゴリ:日本語#せいかく" rel="mw:PageProp/Category"/><link about="#mwt5" href="./カテゴリ:日本語_名 詞#せいかく" id="mwCw" rel="mw:PageProp/Category"/></p>
                <ol>
                    <li>accurate definition.</li>
                </ol>
            </section>
        </body>
    </html>
    """
    parsed = parse_wiktionary_html(mock_html, lang="ja")
    assert "<p>せいかく</p>" in parsed or "せいかく" in parsed
    assert "せいかく)" not in parsed
    assert "正確" not in parsed


def test_parse_wiktionary_html_rokuon():
    mock_html = """
    <html>
        <body>
            <section>
                <h2>日本語</h2>
                <p><span about="#mwt18" data-mw='{"parts":[{"template":{"target":{"wt":"jachar","href":"./テンプレート:jachar"},"params":{"1":{"wt":"録"},"2":{"wt":"音"}},"i":0}}]}' id="mwEg" lang="ja" style="font-family: 'Lucida Sans Unicode', 'Arial Bold', 'Arial', sans-serif;" typeof="mw:Transclusion"><b><a href="./録#日本語" rel="mw:WikiLink" title="録">録</a></b><span typeof="mw:Entity">&nbsp;</span><b><a href="./音#日本語" rel="mw:WikiLink" title="音">音</a></b></span>（ろくおん）</p>
                <ol>
                    <li>recording definition.</li>
                </ol>
            </section>
        </body>
    </html>
    """
    parsed = parse_wiktionary_html(mock_html, lang="ja")
    # Verify the brackets are stripped and we just get the pronunciation
    assert "<p>ろくおん</p>" in parsed or "ろくおん" in parsed
    assert "録" not in parsed
    assert "音" not in parsed
    assert "（ろくおん）" not in parsed  # ensure brackets are gone
    assert "(ろくおん)" not in parsed  # ensure brackets are gone


def test_parse_wiktionary_html_kaikou():
    mock_html = """
    <html>
        <body>
            <section>
                <h2>日本語</h2>
                <p><b><a href="./邂">邂</a> <a href="./逅">逅</a></b>（<a href="./かいこう">かいこう</a>）</p>
                <ol>
                    <li>思いがけなく出会うこと。
                        <ul>
                            <li>偶然を差引いても、（坂口安吾）</li>
                        </ul>
                    </li>
                    <li>思いがけなく出会う。</li>
                </ol>
                <section>
                    <h3>Translations</h3>
                    <ol><li>English translation</li></ol>
                </section>
            </section>
            <section>
                <h2>中国語</h2>
                <p><b>邂逅</b>（xièhòu）</p>
                <ol>
                    <li>Chinese definition here.</li>
                </ol>
            </section>
        </body>
    </html>
    """
    parsed = parse_wiktionary_html(mock_html, lang="ja")
    assert "かいこう" in parsed
    assert "（かいこう）" not in parsed
    assert "邂逅" not in parsed
    assert "思いがけなく出会うこと" in parsed
    assert "偶然を差引いても" in parsed
    assert "English translation" not in parsed  # Translation section removed
    assert "Chinese definition here" not in parsed  # Chinese section removed


def test_parse_wiktionary_html_end_run_multiple_parens():
    """
    When an English word has multiple parenthetical groups in the <p> tag
    (e.g. "(plural end runs) (Canada, US)"), the outer parens must NOT be
    stripped — only strip when the entire content is a single matched pair.
    """
    mock_html = """
    <html>
        <body>
            <p><strong><a href="./end">end</a> <a href="./run">run</a></strong> (<i>plural</i> <b><a href="./end_runs">end runs</a></b>) (<a href="./Canada">Canada</a>, <a href="./US">US</a>)</p>
            <ol>
                <li>(<i>American football</i>) A running play in which the player carrying the ball attempts to avoid being tackled.</li>
                <li>(<i>figuratively, by extension, chiefly informal</i>) An attempt to circumvent a difficult problem by not confronting it directly.</li>
            </ol>
        </body>
    </html>
    """
    parsed = parse_wiktionary_html(mock_html)
    # The p_tag content should preserve both parenthetical groups intact
    assert "(plural" in parsed or "(<i>plural</i>" in parsed
    assert "(Canada, US)" in parsed
    # Must NOT produce broken output like "plural end runs) (Canada, US"
    assert "plural end runs) (Canada, US" not in parsed or "(plural" in parsed


def test_parse_wiktionary_html_kanji_char_hi():
    """
    火 page: the <ol> has no preceding <p> tag. The first <li> starts with
    <b>ひ</b>。definition... — the reading must be extracted into a standalone
    <p> line, not glued to the first definition.
    """
    mock_html = """
    <html>
        <body>
            <section>
                <h2>日本語</h2>
                <section>
                    <h3>名詞・造語成分</h3>
                    <ol>
                        <li><b><a href="./ひ#名詞:火" title="ひ">ひ</a></b>。物が燃えるときに出る炎や熱。
                            <ul><li>火炎、火山、消火、花火、火遊び。</li></ul>
                        </li>
                        <li>燃える。焼く。
                            <ul><li>火事、大火。</li></ul>
                        </li>
                        <li>（か）曜日の一つ。火曜日。</li>
                    </ol>
                </section>
            </section>
        </body>
    </html>
    """
    parsed = parse_wiktionary_html(mock_html, lang="ja")
    # Pronunciation must be a standalone <p> at the top
    assert "<p>ひ</p>" in parsed
    # First definition must NOT start with ひ。
    assert "ひ。" not in parsed
    # Definitions must still be present
    assert "物が燃えるときに出る炎や熱" in parsed
    assert "火炎" in parsed
    assert "燃える" in parsed
    assert "曜日" in parsed


def test_parse_wiktionary_html_kanji_char_multi_reading():
    """
    Kanji pages can list multiple readings in the first <li>, e.g.
    <b>reading1</b> 又は <b>reading2</b>。definition...
    Both readings should be extracted as pronunciation.
    """
    mock_html = """
    <html>
        <body>
            <section>
                <h2>日本語</h2>
                <section>
                    <h3>名詞</h3>
                    <ol>
                        <li><b><a href="./あめ">あめ</a></b> 又は <b><a href="./あま">あま</a></b>。空から降る水。
                            <ul><li>雨天、大雨。</li></ul>
                        </li>
                        <li>比喩的に、多量に降り注ぐもの。</li>
                    </ol>
                </section>
            </section>
        </body>
    </html>
    """
    parsed = parse_wiktionary_html(mock_html, lang="ja")
    # Both readings must be in a standalone pronunciation <p>
    assert "<p>" in parsed
    # Extract the first <p> content
    import re

    p_match = re.search(r'<p>(.*?)</p>', parsed)
    assert p_match is not None, f"No <p> found in: {parsed}"
    p_content = p_match.group(1)
    assert "あめ" in p_content
    assert "あま" in p_content
    # Definitions must still be present
    assert "空から降る水" in parsed
