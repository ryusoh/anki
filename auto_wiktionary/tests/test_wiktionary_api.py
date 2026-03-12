import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import fetch_wiktionary_html, parse_wiktionary_html

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
    assert "(<i>plural</i> <b>jazz dots</b>)" in parsed
    assert "<strong>" not in parsed
    assert "<a " not in parsed # links unwrapped
    assert "Example sentence here" in parsed
    assert "edit" not in parsed # editsection removed

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
    assert "（かいこう）" in parsed
    assert "邂逅" not in parsed
    assert "思いがけなく出会うこと" in parsed
    assert "偶然を差引いても" in parsed
    assert "English translation" not in parsed # Translation section removed
    assert "Chinese definition here" not in parsed # Chinese section removed
