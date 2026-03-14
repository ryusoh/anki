import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from search import build_tier1_query

def test_build_tier1_simple():
    assert build_tier1_query("apple") == "Front:*apple*"

def test_build_tier1_multiple():
    assert build_tier1_query("apple banana") == "Front:*apple* Front:*banana*"

def test_build_tier1_special():
    assert build_tier1_query('apple deck:"my deck" is:due') == 'Front:*apple* deck:"my deck" is:due'

def test_build_tier1_quotes():
    assert build_tier1_query('"apple banana" is:new') == '"Front:*apple banana*" is:new'

def test_build_tier1_or():
    assert build_tier1_query("apple OR banana") == "Front:*apple* OR Front:*banana*"

def test_build_tier1_complex():
    assert build_tier1_query('apple OR "banana split" -tag:hard') == 'Front:*apple* OR "Front:*banana split*" -tag:hard'

def test_build_tier1_no_normal():
    assert build_tier1_query('deck:default is:new') == ""
