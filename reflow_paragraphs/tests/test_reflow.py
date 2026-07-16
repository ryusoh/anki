import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core import reflow_field_html, reflow_text

# Verbatim paste from a PDF book: one paragraph hard-wrapped at the column width.
PDF_PARAGRAPH = """Raskolnikov was unused to crowds and, as has already
been said, he shunned society, recently more than ever. But
now, for some reason, he suddenly felt drawn to other
people. Something new seemed to be stirring inside him,
bringing with it a thirst for human company. A whole month
of intense anguish and dismal excitement had left him so
exhausted that he yearned for at least a moment’s rest in
another world – any world would do – and now he was only
too happy to remain in the den, filthy though it was."""

PDF_PARAGRAPH_REFLOWED = (
    "Raskolnikov was unused to crowds and, as has already been said, he shunned "
    "society, recently more than ever. But now, for some reason, he suddenly felt "
    "drawn to other people. Something new seemed to be stirring inside him, "
    "bringing with it a thirst for human company. A whole month of intense anguish "
    "and dismal excitement had left him so exhausted that he yearned for at least "
    "a moment’s rest in another world – any world would do – and now he was only "
    "too happy to remain in the den, filthy though it was."
)


def test_pdf_wrapped_paragraph_reflows_to_single_line():
    assert reflow_text(PDF_PARAGRAPH) == PDF_PARAGRAPH_REFLOWED


# Verbatim english-explanation card field: definition, quoted example, then
# Similar/Opposite word lists. Line-per-item on purpose — must not be touched.
DICTIONARY_FIELD = """an act of releasing someone from the custody or restraint of the law.
"four days in jail and one year conditional discharge"
Similar:
release
liberation
acquittal
clearance
clearing
absolution
pardon
exoneration
reprieve
amnesty
exculpation
let-off
letting off
manumission
Opposite:
conviction"""


def test_dictionary_format_field_is_left_untouched():
    assert reflow_text(DICTIONARY_FIELD) == DICTIONARY_FIELD


def test_field_html_br_separated_paragraph_reflows():
    html = PDF_PARAGRAPH.replace("\n", "<br>")
    assert reflow_field_html(html) == PDF_PARAGRAPH_REFLOWED


def test_field_html_without_prose_is_returned_byte_identical():
    # If nothing reflows, the field must not be rewritten at all — not even
    # normalizing <br /> to <br>.
    html = DICTIONARY_FIELD.replace("\n", "<br />")
    assert reflow_field_html(html) == html


def test_field_html_with_br_plus_literal_newlines_reflows():
    # Regression: real Anki fields store "<br>\n" per line break. The literal
    # newline is HTML whitespace, not a second break — treating it as one
    # produced phantom blank lines and doubled spacing instead of reflowing.
    html = PDF_PARAGRAPH.replace("\n", "<br>\n")
    assert reflow_field_html(html) == PDF_PARAGRAPH_REFLOWED


def test_structured_wiktionary_field_is_untouched():
    # Regression: a real Wiktionary definition field nests block HTML with
    # literal newlines and zero <br>. Treating <div> boundaries as line
    # breaks exploded it into 2-5 blank lines per line. Divs are structure:
    # the field must come back byte-identical.
    html = (
        '<ul><p><i>comparative</i> <b>more dire</b></p>'
        '<li><span>Disastrous</span>, calamitous.\n'
        '<dl><dd><span><span>Synonyms:</span> <span>cataclysmic</span>, '
        '<span>ruinous</span></span></dd>\n'
        '<dd><div><i>He received a <b>dire</b> compensation.</i></div></dd></dl></li>'
        '<li>Causing despair; gloomy and bleak.\n'
        '<dl><dd><div><span>Their efforts thereafter had an air of desperation '
        'as their <b>dire</b> 2012 league form continued.</span></div></dd></dl></li></ul>'
    )
    assert reflow_field_html(html) == html


def test_div_per_line_prose_reflows_without_touching_nested_divs():
    # Regression (real 'anguish' card): PDF paste can arrive as one leaf
    # <div><i>line</i></div> per wrapped line, adjacent to a deeply nested
    # dictionary div-soup. Only the run of leaf line-divs may be joined; the
    # nested structure must stay byte-identical.
    soup = (
        '<div><i>noun</i><br></div>'
        '<div><div><div>severe mental or physical pain or suffering.</div>'
        '<div><div>"she shut her eyes&nbsp;<b>in anguish</b>"</div></div>'
        '<div><div>Similar:</div></div>'
        '<div><div>agony<div><div></div></div></div></div>'
        '<div><div>torment<div><div></div></div></div></div>'
    )
    prose = "\n".join(f"<div><i>{line}</i></div>" for line in PDF_PARAGRAPH.split("\n"))
    sound = "[sound:googletts-abc123.mp3]"
    html = f"{soup}<div>{prose}{sound}</div></div>"

    joined = " ".join(f"<i>{line}</i>" for line in PDF_PARAGRAPH.split("\n"))
    expected = f"{soup}<div><div>{joined}</div>{sound}</div></div>"
    assert reflow_field_html(html) == expected


def test_definition_with_lowercase_example_and_header_is_untouched():
    # Regression (real 'foible' card): a glossary block of definition, a
    # lowercase example sentence, and a header line. The example starting
    # lowercase after a '.'-ended definition must not read as a wrap.
    html = (
        "<div>a minor weakness or eccentricity in someone's character.</div>"
        "<div>they have to tolerate each other's little foibles</div>"
        "<div>同義語:</div>"
    )
    assert reflow_field_html(html) == html


def test_cjk_glossary_marker_lines_are_untouched():
    # Regression (real 'foible' card): 【英】/【考】/【记】 marker lines, a short
    # POS heading, and an etymology paragraph are deliberate separate lines.
    html = (
        "<b>【英】</b> n. 小缺点，小毛病(a small weakness; fault)<br>"
        "<b>【考】</b> foible : flaw / quibble : objection(程度: 小缺点, 缺点)<br>"
        "<b>【记】</b> 可能来自feeble(脆弱 的)<br>"
        "foible (n.) <br>"
        '1640s, "weak point of a sword blade" (contrasted to forte), from French '
        'foible (n.), from obsolete foible (adj.) "weak". Related: Foibles.<br>'
        "n. (性格上的)小缺点; 小毛病 = fault"
    )
    assert reflow_field_html(html) == html


def test_leaf_div_word_list_is_untouched():
    # Adjacent leaf divs holding list items (short visible text) are a run,
    # but must never be joined.
    html = '<div>Similar:</div>\n<div>agony</div>\n<div>pain</div>\n<div>torment</div>'
    assert reflow_field_html(html) == html


def test_mixed_field_reflows_only_the_prose_run():
    # Real paste target: a field holding a styled dictionary head with a list,
    # an image, the <i>-wrapped hard-wrapped PDF lines, and a [sound:…] ref.
    # Only the prose run may change; everything else stays verbatim.
    head = (
        '<span style="color: rgb(112, 117, 122);">noun</span>:&nbsp;<b>chintz</b> '
        '<ol><li>printed multicolored cotton fabric with a glazed finish, used '
        'especially for curtains and upholstery. "floral chintz curtains"<br>'
        '</li></ol><img src="paste-abc123.jpg">'
    )
    prose_lines = "<br>".join(f"<i>{line}</i>" for line in PDF_PARAGRAPH.split("\n"))
    sound = "[sound:forvo-abc123.mp3]"
    html = f"{head}<br>{prose_lines}<br>{sound}"

    joined_prose = " ".join(f"<i>{line}</i>" for line in PDF_PARAGRAPH.split("\n"))
    expected = f"{head}<br>{joined_prose}<br>{sound}"
    assert reflow_field_html(html) == expected


def test_blank_line_keeps_paragraphs_separate():
    two_paragraphs = PDF_PARAGRAPH + "\n\n" + PDF_PARAGRAPH
    expected = PDF_PARAGRAPH_REFLOWED + "\n\n" + PDF_PARAGRAPH_REFLOWED
    assert reflow_text(two_paragraphs) == expected


def test_end_of_line_hyphenation_joins_without_hyphen():
    wrapped = (
        "A whole month of intense anguish and dismal excitement had left him so ex-\n"
        "hausted that he yearned for at least a moment’s rest in another world."
    )
    expected = (
        "A whole month of intense anguish and dismal excitement had left him so "
        "exhausted that he yearned for at least a moment’s rest in another world."
    )
    assert reflow_text(wrapped) == expected


def test_adjacent_wrapped_paragraphs_without_blank_line_reflow_separately():
    # PDFs often separate paragraphs only by indentation, which paste discards:
    # two wrapped paragraphs arrive adjacent. The short last line of the first
    # paragraph is the boundary signal.
    pasted = """Raskolnikov was unused to crowds and, as has already
been said, he shunned society, recently more than
ever. But now he suddenly felt drawn to
other people.
The orange is definitely a vibe that we will miss over
time. But those old HPS lights were very inefficient
and it makes sense to replace them."""
    expected = (
        "Raskolnikov was unused to crowds and, as has already been said, "
        "he shunned society, recently more than ever. But now he suddenly "
        "felt drawn to other people.\n"
        "The orange is definitely a vibe that we will miss over time. "
        "But those old HPS lights were very inefficient and it makes sense "
        "to replace them."
    )
    assert reflow_text(pasted) == expected


def test_adjacent_full_paragraphs_are_not_merged():
    # Already-normal paragraphs on adjacent lines: every line ends a sentence
    # and the next starts uppercase, so nothing looks like a wrap artifact.
    text = (
        "High-pressure sodium (HPS) lamps are a type of gas-discharge lamp "
        "that use sodium vapor to produce light, commonly found in street "
        "lighting and security applications.\n"
        "The orange is definitely a vibe that we will miss over time. But, "
        "those old HPS lights were very inefficient.\n"
        "Just too bad they can't put them up in a low K setting to keep the old feel."
    )
    assert reflow_text(text) == text


def test_multiword_phrase_list_is_not_joined():
    # Synonym lists can hold multi-word phrases: short lines without sentence
    # punctuation must still read as list items, not as wrapped prose.
    text = """Similar:
letting off
setting free
letting go"""
    assert reflow_text(text) == text


def test_reflow_is_idempotent():
    once = reflow_field_html(PDF_PARAGRAPH.replace("\n", "<br>"))
    assert reflow_field_html(once) == once
    dict_once = reflow_field_html(DICTIONARY_FIELD.replace("\n", "<br>"))
    assert reflow_field_html(dict_once) == dict_once


def test_colon_ended_long_line_is_not_structural():
    # A long column-filling line ending in a colon is not treated as a structural list header.
    text = (
        "The quick brown fox jumps over the lazy dog and the furniture was no better:\n"
        "three old chairs, not in the best repair; a painted table."
    )
    expected = (
        "The quick brown fox jumps over the lazy dog and the furniture was no better: "
        "three old chairs, not in the best repair; a painted table."
    )
    assert reflow_text(text) == expected


def test_user_reported_paragraph_reflows_fully():
    # Test case from user bug report where a colon at the end of a long wrapped
    # line (part of the narrative) previously caused it to be classified as a
    # structural header boundary, split, and partially un-reflowed.
    text = (
        "He woke up late the next day, unrefreshed, after a troubled\n"
        "night’s sleep. He woke up sour, irritable and angry, and\n"
        "looked with loathing at his garret. It was a tiny little cell,\n"
        "about six paces in length, and a truly wretched sight with\n"
        "its dusty, yellowy, peeling wallpaper and a ceiling low\n"
        "enough to terrify even the modestly tall – you could bang\n"
        "your head at any moment. The furniture was no better:\n"
        "three old chairs, not in the best repair; a painted table in\n"
        "the corner, on which lay several books and notebooks,\n"
        "under a layer of dust so thick that no hand could have\n"
        "touched them for many a day; and, lastly, a large ungainly\n"
        "couch which took up virtually the entire length of the wall\n"
        "and half the width of the room. Once upholstered in chintz,\n"
        "now in tatters, it served Raskolnikov for his bed. He often\n"
        "slept on it without bothering to undress and without sheets,\n"
        "covering himself in his old threadbare student coat and\n"
        "resting his head on a small pillow, which he bolstered by\n"
        "placing all the linen he had, clean or worn, beneath it. In\n"
        "front of the couch stood a little table."
    )
    expected = (
        "He woke up late the next day, unrefreshed, after a troubled "
        "night’s sleep. He woke up sour, irritable and angry, and "
        "looked with loathing at his garret. It was a tiny little cell, "
        "about six paces in length, and a truly wretched sight with "
        "its dusty, yellowy, peeling wallpaper and a ceiling low "
        "enough to terrify even the modestly tall – you could bang "
        "your head at any moment. The furniture was no better: "
        "three old chairs, not in the best repair; a painted table in "
        "the corner, on which lay several books and notebooks, "
        "under a layer of dust so thick that no hand could have "
        "touched them for many a day; and, lastly, a large ungainly "
        "couch which took up virtually the entire length of the wall "
        "and half the width of the room. Once upholstered in chintz, "
        "now in tatters, it served Raskolnikov for his bed. He often "
        "slept on it without bothering to undress and without sheets, "
        "covering himself in his old threadbare student coat and "
        "resting his head on a small pillow, which he bolstered by "
        "placing all the linen he had, clean or worn, beneath it. In "
        "front of the couch stood a little table."
    )
    assert reflow_text(text) == expected


def test_user_reported_short_paragraph_with_sentence_break_reflows():
    # Test case from user bug report: a short 3-line paragraph that contains
    # an internal sentence boundary (ending with '.') should still reflow.
    text = (
        "When the soup arrived and he set about eating, Nastasya\n"
        "sat down next to him on the couch and began nattering.\n"
        "She was a village girl and liked a good natter."
    )
    expected = (
        "When the soup arrived and he set about eating, Nastasya "
        "sat down next to him on the couch and began nattering. "
        "She was a village girl and liked a good natter."
    )
    assert reflow_text(text) == expected
def test_open_junction_terminal_char_bypass():
    # If visible length is < MIN_FILL_LEN (e.g. 10) but it ends with a terminal char,
    # it shouldn't be counted as an open junction.
    text = "Short end.\nNext starts uppercase."
    from reflow_paragraphs.core import _is_wrapped_prose
    assert not _is_wrapped_prose(text.split("\n"))
def test_open_junction_short_ends_in_terminal_char():
    # If a short line ends in a terminal char, it's not an open junction.
    from reflow_paragraphs.core import _open_junction
    assert not _open_junction("Short.", "next starts lowercase.")
