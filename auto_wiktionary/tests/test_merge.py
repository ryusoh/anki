import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import merge_definition

def test_merge_definition_empty():
    assert merge_definition("", "<ul><li>def</li></ul>") == "<ul><li>def</li></ul>"
    assert merge_definition("   ", "<ul><li>def</li></ul>") == "<ul><li>def</li></ul>"

def test_merge_definition_existing():
    assert merge_definition("existing content", "<ul><li>def</li></ul>") == "<ul><li>def</li></ul><br>existing content"
    assert merge_definition("old line 1<br>old line 2", "<ul><li>def</li></ul>") == "<ul><li>def</li></ul><br>old line 1<br>old line 2"

