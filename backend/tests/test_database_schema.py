import unittest

from backend.app.database import WatchlistInsightBaselineDB, _missing_columns


class DatabaseSchemaTests(unittest.TestCase):
    def test_watchlist_insight_baseline_has_unique_user_stock_identity(self):
        constraints = WatchlistInsightBaselineDB.__table__.constraints
        unique_columns = {
            tuple(column.name for column in constraint.columns)
            for constraint in constraints
            if constraint.__class__.__name__ == "UniqueConstraint"
        }

        self.assertIn(("user_id", "stock_code"), unique_columns)

    def test_missing_columns_returns_only_absent_columns(self):
        required = {
            "english_name": "english_name VARCHAR(100) DEFAULT ''",
            "ts_code": "ts_code VARCHAR(20) DEFAULT ''",
        }

        missing = _missing_columns({"code", "name", "ts_code"}, required)

        self.assertEqual(missing, {"english_name": "english_name VARCHAR(100) DEFAULT ''"})


if __name__ == "__main__":
    unittest.main()
