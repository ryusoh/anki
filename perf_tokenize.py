import re
import timeit

STOP_WORDS = {'the', 'and'}

def tokenize_old(text, min_length=3, use_stop_words=True):
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    tokens = [w for w in words if len(w) >= min_length]
    if use_stop_words:
        tokens = [w for w in tokens if w not in STOP_WORDS]
    return tokens

_PATTERN = re.compile(r'\b[a-z]+\b')
def tokenize_new(text, min_length=3, use_stop_words=True):
    words = _PATTERN.findall(text.lower())
    if use_stop_words:
        return [w for w in words if len(w) >= min_length and w not in STOP_WORDS]
    return [w for w in words if len(w) >= min_length]

text = "This is a sample text with many words, some of which are long enough and some are not. It should process quickly!" * 100

print("Old:", timeit.timeit(lambda: tokenize_old(text), number=1000))
print("New:", timeit.timeit(lambda: tokenize_new(text), number=1000))
