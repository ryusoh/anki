import sys
from unittest.mock import MagicMock

# Mock out aqt entirely so we can import the module outside of Anki
sys.modules['aqt'] = MagicMock()
sys.modules['aqt.editor'] = MagicMock()

from strip_html_tags import _strip_selection

# Test Case 1: Partial line selection shouldn't strip surrounding tags
def test_partial_selection():
    html = '<h3><span style="font-size: 20px;">The quick brown fox jumps over the lazy dog.</span><br></h3><div>Some other text block.</div>'
    selected = "brown fox jumps"
    
    res = _strip_selection(html, selected)
    assert res == html

# Test Case 2: Inner tags inside partial selection SHOULD be stripped
def test_inner_tags_stripped():
    html = '<h3><span style="font-size: 20px;">The quick </span><b>brown fox</b><span style="font-size: 20px;"> jumps over the lazy dog.</span><br></h3><div>Some other text block.</div>'
    selected = "The quick brown fox jumps over the lazy dog."
    
    res = _strip_selection(html, selected)
    # "The quick brown fox jumps over the lazy dog." is fully enclosed by the <h3> tag.
    # The script will now strip the <h3> and the <br> inside it, and replace the whole block
    # with a generic <div> to prevent merging with adjacent blocks.
    expected = '<div>The quick brown fox jumps over the lazy dog.</div><div>Some other text block.</div>'
    
    assert res == expected

# Test Case 3: Invisible characters and HTML entities mapping
def test_html_entities_and_invisible_chars():
    html = '<div><b>Rule:</b> Data is not lost.&nbsp;</div>\n<div><b>Implementation:</b> Stateful Repair.</div>'
    selected = "Rule: Data is not lost. "
    
    res = _strip_selection(html, selected)
    expected = '<div>Rule: Data is not lost.&nbsp;</div>\n<div><b>Implementation:</b> Stateful Repair.</div>'
    assert res == expected

# Test Case 4: Smart Block Replacement (Full block selection)
def test_block_replacement():
    html = '<div><h3><b>1.3 Section Title</b></h3></div><div><ul><li><div>Item 1</div></li></ul></div>'
    selected = "1.3 Section Title"
    
    res = _strip_selection(html, selected)
    expected = '<div><div>1.3 Section Title</div></div><div><ul><li><div>Item 1</div></li></ul></div>'
    assert res == expected

# Test Case 5: Smart Block Replacement near Lists
def test_block_replacement_near_lists():
    html = '<h3><span>Some text.</span> <b>Bypass</b> <span>Standard stack.</span><br></h3><ul><li><div>Item 1</div></li></ul>'
    selected = "Some text. Bypass Standard stack."
    
    res = _strip_selection(html, selected)
    expected = '<div>Some text. Bypass Standard stack.</div><ul><li><div>Item 1</div></li></ul>'
    assert res == expected

# Test Case 6: Unicode space normalization
def test_unicode_space_normalization():
    # Using an EN SPACE (\u2002) in the HTML
    html = '<div><h3><b>1.3 Section Title</b></h3></div>'
    selected = "1.3 Section Title" # also has EN SPACE
    
    res = _strip_selection(html, selected)
    expected = '<div><div>1.3 Section Title</div></div>'
    assert res == expected
