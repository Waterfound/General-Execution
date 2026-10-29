import unittest

from wrm_pdf_table_probe import PDF_TEXT, convert_and_validate


class PdfTableProbeTests(unittest.TestCase):
    def test_public_fixture_is_complete_and_math_consistent(self):
        result, csv_text = convert_and_validate()
        self.assertEqual("PASS", result["verdict"])
        self.assertEqual(36, result["rows"])
        self.assertEqual(396, result["data_values_checked"])
        self.assertEqual(37, len(csv_text.splitlines()))

    def test_numeric_corruption_fails_closed(self):
        corrupted = PDF_TEXT.replace("1 0.000 1.000", "1 0.000 1.001", 1)
        result, _ = convert_and_validate(corrupted)
        self.assertEqual("FAIL", result["verdict"])
        self.assertEqual("1", result["failures"][0]["df"])

    def test_missing_column_fails_closed(self):
        corrupted = PDF_TEXT.replace("1 0.000 1.000", "1 0.000", 1)
        result, _ = convert_and_validate(corrupted)
        self.assertEqual("FAIL", result["verdict"])
        self.assertEqual("column_count", result["failures"][0]["reason"])


if __name__ == "__main__":
    unittest.main()
