import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app


class NumerologyTests(unittest.TestCase):
    def test_calculation_preserves_master_number(self):
        result = app.calculate_map("Thargelia Gilda de Miranda Cousseiro Neta", "1960-02-29", 2027)
        self.assertEqual(result["birth_day"]["result"], 11)
        self.assertEqual(result["motivation"]["result"], 5)
        self.assertEqual(result["expression"]["result"], 8)
        self.assertEqual(result["personal_year"]["result"], 6)

    def test_accents_and_hyphens_are_accepted(self):
        result = app.calculate_map("Ana-Cláudia de Sá", "1987-12-10", 2027)
        self.assertEqual(result["name"], "Ana-Cláudia de Sá")
        self.assertIn(result["destiny"]["result"], (2, 11))

    def test_unknown_items_are_explicitly_unsupported(self):
        result = app.calculate_map("Maria", "1990-01-01", 2027)
        self.assertIn("Dívida Cármica", result["unsupported"])
        self.assertIn("Triângulo da Vida completo", result["unsupported"])


if __name__ == "__main__":
    unittest.main()
