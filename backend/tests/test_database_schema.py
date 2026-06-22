import unittest

from backend.app.database import _missing_columns


class DatabaseSchemaTests(unittest.TestCase):
    def test_missing_columns_returns_only_absent_columns(self):
        required = {
            "english_name": "english_name VARCHAR(100) DEFAULT ''",
            "ts_code": "ts_code VARCHAR(20) DEFAULT ''",
        }

        missing = _missing_columns({"code", "name", "ts_code"}, required)

        self.assertEqual(missing, {"english_name": "english_name VARCHAR(100) DEFAULT ''"})


if __name__ == "__main__":
    unittest.main()
