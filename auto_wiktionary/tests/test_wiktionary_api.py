import json

from auto_wiktionary.utils import (
    fetch_wiktionary_html,
    format_candidates_html,
    get_wiktionary_candidates,
    parse_wiktionary_html,
)


def _mock_opensearch(json_payload):
    """Build a urlopen mock returning a canned opensearch JSON body."""
    from unittest.mock import MagicMock

    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(json_payload).encode("utf-8")
    mock_urlopen = MagicMock()
    mock_urlopen.return_value.__enter__.return_value = mock_response
    return mock_urlopen


def test_get_wiktionary_candidates_returns_suggestions():
    from unittest.mock import patch

    # opensearch returns [search, [suggestions], [descriptions], [urls]]
    payload = ["applz", ["apple", "apply", "applet"], [], []]
    with patch("urllib.request.urlopen", _mock_opensearch(payload)):
        candidates = get_wiktionary_candidates("applz", "en")
    assert candidates == ["apple", "apply", "applet"]


def test_get_wiktionary_candidates_no_matches():
    from unittest.mock import patch

    payload = ["ajsfkldsjafkljsdaf", [], [], []]
    with patch("urllib.request.urlopen", _mock_opensearch(payload)):
        candidates = get_wiktionary_candidates("ajsfkldsjafkljsdaf", "en")
    assert candidates == []


def test_get_wiktionary_candidates_empty_input_skips_network():
    from unittest.mock import patch

    # Empty word must short-circuit before any network call.
    with patch("urllib.request.urlopen") as mock_urlopen:
        assert get_wiktionary_candidates("", "en") == []
        mock_urlopen.assert_not_called()


def test_get_wiktionary_candidates_network_error():
    from unittest.mock import patch
    from urllib.error import URLError

    with (
        patch("urllib.request.urlopen", side_effect=URLError("offline")),
        # Keep the proxy fallback from probing real localhost ports in tests.
        patch("auto_wiktionary.proxy_fallback._detect_local_proxy", return_value=None),
    ):
        # Failures are swallowed and yield an empty list, never raise.
        assert get_wiktionary_candidates("applz", "en") == []


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
    assert "Error" in res or res == ""


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


def test_parse_wiktionary_html_kikou_ul_definition():
    """
    ja.wiktionary pages for single-gloss words (e.g. 起工) put the definition
    in a <ul>, not an <ol> — the parser must not return "" for them.
    Structure mirrors the real rest_v1 payload for 起工.
    """
    mock_html = """
    <html>
        <body>
            <section>
                <h2>日本語</h2>
                <section>
                    <h3>名詞</h3>
                    <p><b><a href="./起">起</a><a href="./工">工</a></b>（<a href="./きこう">きこう</a>）</p>
                    <ul>
                        <li>（<a href="./建築">建築</a>などの）<a href="./工事">工事</a>を始めること。</li>
                    </ul>
                </section>
                <section>
                    <h3>翻訳</h3>
                    <ul><li>English: start of construction</li></ul>
                </section>
            </section>
        </body>
    </html>
    """
    parsed = parse_wiktionary_html(mock_html, lang="ja")
    assert parsed != ""
    assert "きこう" in parsed
    assert "工事を始めること" in parsed
    assert "start of construction" not in parsed  # Translation section removed


def test_parse_wiktionary_html_yusugu_pronunciation_section_excluded():
    """
    ja.wiktionary verb pages (e.g. ゆすぐ) carry a 発音 section whose content
    is a <ul> of accent/IPA items. Those are not definitions and must not leak
    into the output — mirrors the real rest_v1 payload for ゆすぐ.
    """
    mock_html = """
    <html>
        <body>
            <section>
                <h2>日本語</h2>
                <section>
                    <h3>動詞：濯</h3>
                    <p><strong>ゆすぐ</strong></p>
                    <ol>
                        <li>水の中で揺り動かして汚れを落とす。</li>
                    </ol>
                </section>
                <section>
                    <h3>発音</h3>
                    <ul>
                        <li>(東京式) ゆすぐ [yùsúgú] (平板型 – [0])</li>
                        <li>IPA: [jɯ̟ᵝsɨᵝɡɯ̟ᵝ]</li>
                    </ul>
                </section>
            </section>
        </body>
    </html>
    """
    parsed = parse_wiktionary_html(mock_html, lang="ja")
    assert "水の中で揺り動かして汚れを落とす" in parsed
    assert "東京式" not in parsed
    assert "IPA" not in parsed
    assert "平板型" not in parsed


def test_parse_wiktionary_html_kansuu_etymology_section():
    """
    ja.wiktionary pages with a 語源 (etymology) section before the POS section
    (e.g. 関数) used to emit the etymology <li> first, pushing the headword
    pronunciation <p> into the middle of the <ul> where Anki drops it.
    Non-definition sections (語源, 合成語, 関連項目) must be removed so the
    pronunciation <p> lands at the top. Mirrors the real rest_v1 payload
    for 関数.
    """
    mock_html = """
    <html>
        <body>
            <section>
                <h2>日本語</h2>
                <section>
                    <h3>語源</h3>
                    <ol>
                        <li>戦前は、ファンクションの中国語音訳語「函數」から「関数」に書き換えられた。</li>
                    </ol>
                </section>
                <section>
                    <h3>発音</h3>
                    <ul>
                        <li>かんすう [kàɴsɯ́ɯ̀]</li>
                    </ul>
                </section>
                <section>
                    <h3>名詞</h3>
                    <p id="mwFQ"><strong class="Jpan headword" lang="ja"><a href="./関#日本語" title="関">関</a><a href="./数#日本語" title="数">数</a></strong><span> (</span><span class="headword-tr manual-tr tr" dir="ltr"><a href="./かんすう" title="かんすう">かんすう</a></span><span>)</span></p>
                    <ol>
                        <li>ある変数に依存して決まる値あるいはその対応を表す式。</li>
                        <li>数の集合に限らない写像。</li>
                    </ol>
                </section>
                <section>
                    <h3>合成語</h3>
                    <ul>
                        <li>実関数、複素関数、汎関数</li>
                    </ul>
                </section>
                <section>
                    <h3>関連項目</h3>
                    <ul>
                        <li>プロジェクト:数学/函数と関数</li>
                    </ul>
                </section>
            </section>
        </body>
    </html>
    """
    parsed = parse_wiktionary_html(mock_html, lang="ja")
    # Pronunciation must be the first element, right after <ul>
    assert parsed.startswith("<ul><p>かんすう</p>"), f"Unexpected output: {parsed}"
    # Definitions must still be present
    assert "ある変数に依存して決まる値" in parsed
    assert "数の集合に限らない写像" in parsed
    # Non-definition sections must not leak into the output
    assert "語源" not in parsed
    assert "函數" not in parsed
    assert "実関数" not in parsed
    assert "プロジェクト" not in parsed


def test_parse_wiktionary_html_menseki_new_heading_markup():
    """
    New wrinkle: the Wiktionary parse API no longer wraps sections in
    <section> elements — headings are flat <div class="mw-heading
    mw-headingN"> siblings under div.mw-parser-output. The section-based
    filters silently no-op on this markup, so on multi-language pages like
    面積 the 中国語 section (官話/拼音 pronunciations) and the 参考文献
    citation list (↑ 黃河清…) leaked into the parsed definition.
    Trimmed from the real ja.wiktionary parse payload for 面積.
    """
    mock_html = """
    <div class="mw-content-ltr mw-parser-output" lang="ja" dir="ltr">
        <div class="mw-heading mw-heading2"><h2 id="日本語">日本語</h2></div>
        <div class="mw-heading mw-heading3"><h3>語源</h3></div>
        <p>「めん」+「せき」<sup class="reference"><a href="#cite_note-1">[1]</a></sup></p>
        <div class="mw-heading mw-heading3"><h3>発音</h3></div>
        <ul>
            <li>(東京式) めんせき [méꜜǹsèkì] (頭高型 – [1])</li>
        </ul>
        <div class="mw-heading mw-heading3"><h3>名詞</h3></div>
        <p><strong class="Jpan headword" lang="ja">面積</strong><span> (</span><span class="headword-tr manual-tr tr" dir="ltr">めんせき</span><span>)</span></p>
        <ol>
            <li>平面の広さ。</li>
        </ol>
        <div class="mw-heading mw-heading4"><h4>関連語</h4></div>
        <ul>
            <li>表面積</li>
        </ul>
        <div class="mw-heading mw-heading3"><h3>参考文献</h3></div>
        <div class="mw-references-wrap">
            <ol class="references">
                <li id="cite_note-1"><span>↑</span> <span>黃河清, 利玛窦对汉语的贡献, 2003</span></li>
            </ol>
        </div>
        <div class="mw-heading mw-heading2"><h2 id="中国語">中国語</h2></div>
        <div class="mw-heading mw-heading3"><h3>発音</h3></div>
        <ul>
            <li>官話: 拼音 miànjī</li>
        </ul>
        <div class="mw-heading mw-heading3"><h3>名詞</h3></div>
        <ol>
            <li>平面的大小。</li>
        </ol>
        <div class="mw-heading mw-heading2"><h2 id="朝鮮語">朝鮮語</h2></div>
        <div class="mw-heading mw-heading3"><h3>名詞</h3></div>
        <ol>
            <li>면적。</li>
        </ol>
    </div>
    """
    parsed = parse_wiktionary_html(mock_html, lang="ja")
    # Reading from the 名詞 headword lands at the top
    assert parsed.startswith("<ul><p>めんせき</p>"), f"Unexpected output: {parsed}"
    # Japanese definition kept
    assert "平面の広さ" in parsed
    # 語源/発音/関連語 and the 参考文献 citation list must not leak
    assert "黃河清" not in parsed
    assert "利玛窦" not in parsed
    assert "東京式" not in parsed
    assert "表面積" not in parsed
    # Non-Japanese language sections must not leak
    assert "官話" not in parsed
    assert "拼音" not in parsed
    assert "平面的大小" not in parsed
    assert "면적" not in parsed


def test_fetch_wiktionary_html_error():
    from unittest.mock import patch
    from urllib.error import HTTPError

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = HTTPError(
            "url", 500, "Internal Server Error", {}, None
        )  # pyright: ignore[reportArgumentType]
        res = fetch_wiktionary_html("error_word", "en")
        assert res == "Error: 500"
