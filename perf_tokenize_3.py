import re
import timeit

text = "This is a sample text with many words, some of which are long enough and some are not. It should process quickly!" * 100

def tokenize_old(text, min_length=3, use_stop_words=True):
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    tokens = [w for w in words if len(w) >= min_length]
    if use_stop_words:
        # Assuming STOP_WORDS is imported and used
        pass
    return tokens

# Compile the regex globally with min_length=3
_pattern_cache = {}
def get_pattern(min_length):
    if min_length not in _pattern_cache:
        _pattern_cache[min_length] = re.compile(rf'\b[a-z]{{{min_length},}}\b')
    return _pattern_cache[min_length]

def tokenize_new(text, min_length=3, use_stop_words=True):
    # Ignoring stop words for a moment
    return get_pattern(min_length).findall(text.lower())

print("Old:", timeit.timeit(lambda: tokenize_old(text), number=1000))
print("New:", timeit.timeit(lambda: tokenize_new(text), number=1000))
