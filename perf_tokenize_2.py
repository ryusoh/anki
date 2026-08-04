import re
import timeit

text = "This is a sample text with many words, some of which are long enough and some are not. It should process quickly!" * 100

def tokenize_old(text, min_length=3, use_stop_words=True):
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    tokens = [w for w in words if len(w) >= min_length]
    return tokens

# Can we compile the regex and use {min_length,} directly?
pattern = re.compile(r'\b[a-z]{3,}\b')
def tokenize_new(text, min_length=3, use_stop_words=True):
    return pattern.findall(text.lower())

print("Old:", timeit.timeit(lambda: tokenize_old(text), number=1000))
print("New:", timeit.timeit(lambda: tokenize_new(text), number=1000))
