import unittest
import json
import gzip
import os
import shutil
from pathlib import Path
from data.anki.security_check import check_file_for_private_data

class TestSecurityGuardrail(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("data/anki/tests/tmp_security")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.leaked_file = self.test_dir / "notes.json.gz"

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_notes_anonymization_guardrail(self):
        """Test that security check fails if notes.json.gz contains private fields."""
        # Create a "leaked" notes file with private flds
        leaked_data = [
            {"id": 1, "guid": "abc", "mid": 100, "flds": "private content", "tags": "private tag"}
        ]
        
        with gzip.open(self.leaked_file, "wt", encoding="utf-8") as f:
            json.dump(leaked_data, f)
            
        # Run the check
        violations = check_file_for_private_data(str(self.leaked_file), "")
        
        # Verify it caught the leak
        self.assertTrue(any(v['type'] == 'data_leak_regression' for v in violations), 
                        "Security check should have caught the data leak in notes.json.gz")
        
        # Verify it specifically mentions flds/tags
        regression = next(v for v in violations if v['type'] == 'data_leak_regression')
        self.assertIn("flds", regression['fields'])
        self.assertIn("tags", regression['fields'])

    def test_anonymized_notes_passes(self):
        """Test that properly anonymized notes.json.gz passes the check."""
        clean_data = [
            {"id": 1, "guid": "abc", "mid": 100}
        ]
        
        with gzip.open(self.leaked_file, "wt", encoding="utf-8") as f:
            json.dump(clean_data, f)
            
        # Run the check
        violations = check_file_for_private_data(str(self.leaked_file), "")
        
        # Verify no regressions found
        regressions = [v for v in violations if v['type'] == 'data_leak_regression']
        self.assertEqual(len(regressions), 0, "Clean anonymized file should not have violations")

if __name__ == "__main__":
    unittest.main()
