import ast
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from backend.app.routers import stocks


class StockDetailAssemblerBoundaryTests(unittest.TestCase):
    def test_get_stock_detail_delegates_to_assembler(self):
        expected = object()

        with patch.object(stocks, "assemble_stock_detail", return_value=expected, create=True) as assemble:
            try:
                result = stocks.get_stock_detail(Mock(), "600000", update_realtime=False)
            except Exception:
                result = None

        self.assertIs(result, expected)
        assemble.assert_called_once()

    def test_get_stock_detail_router_boundary_contains_only_delegation(self):
        source_path = Path(stocks.__file__)
        module = ast.parse(source_path.read_text(encoding="utf-8"))
        function = next(
            node
            for node in module.body
            if isinstance(node, ast.FunctionDef) and node.name == "get_stock_detail"
        )

        self.assertEqual(len(function.body), 1)
        self.assertIsInstance(function.body[0], ast.Return)


if __name__ == "__main__":
    unittest.main()
