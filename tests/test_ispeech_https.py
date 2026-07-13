import sys
import unittest


class TestISpeechHttps(unittest.TestCase):
    def test_https(self):
        with open('awesome_tts/awesometts/service/ispeech.py', 'r') as f:
            content = f.read()
            self.assertIn("https://api.ispeech.org/api/rest", content)
            self.assertNotIn("http://api.ispeech.org/api/rest", content)


if __name__ == '__main__':
    unittest.main()
