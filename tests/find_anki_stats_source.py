import os
import sys


def search_files():
    for root, _dirs, files in os.walk(os.path.expanduser('~')):
        for file in files:
            if file == 'stats.js' or file.endswith('bundle.js'):
                print(os.path.join(root, file))


# We can also just run python to see if we can find any Anki install
