import unittest

from workloads.rls_v12_conformance.engine import ValidationError
from workloads.rls_v12_conformance.ibkr_usa_snapshot_candidate_v1_2 import (
    PROTOCOL_VERSION,
    validate_ibkr_usa_snapshot_v12,
)

HEADER = "#SYM|CUR|NAME|CON|ISIN|REBATERATE|FEERATE|AVAILABLE|FIGI|"


def snapshot(rows, bof="#BOF|2025.06.18|04:54:55", eof_count=None, header=HEADER):
    count = len(rows) if eof_count is None else eof_count
    return "\r\n".join([bof, header, *rows, f"#EOF|{count}", ""]).encode()


def row(sym="AAA", con=1001, fee="1.25", available="5000", rebate="0.25", isin="US0378331005", figi="BBG000B9XRY4"):
    return f"{sym}|USD|Example Corp|{con}|{isin}|{rebate}|{fee}|{available}|{figi}|"


class CandidateV12Conformance(unittest.TestCase):
    def test_modern_schema_and_figi(self):
        r = validate_ibkr_usa_snapshot_v12(snapshot([row()]))
        self.assertEqual(r.protocol_version, PROTOCOL_VERSION)
        self.assertTrue(r.structurally_valid)
        self.assertEqual(r.rows[0].figi, "BBG000B9XRY4")
        self.assertEqual(r.rows[0].fee_rate_bps, "125")

    def test_na_rates_remain_missing_with_positive_availability(self):
        r = validate_ibkr_usa_snapshot_v12(snapshot([row(fee="NA", rebate="NA", available="100")]))
        self.assertIsNone(r.rows[0].fee_rate_percent)
        self.assertIsNone(r.rows[0].rebate_rate_percent)
        self.assertEqual(r.rows[0].availability_state, "OBSERVED_AVAILABLE")
        self.assertEqual(r.availability_with_missing_fee_rows, 1)
        self.assertEqual(r.paired_fee_availability_rows, 0)

    def test_blank_fee_independent_from_lower_bound_availability(self):
        r = validate_ibkr_usa_snapshot_v12(snapshot([row(fee="", available=">10000000")]))
        self.assertIsNone(r.rows[0].fee_rate_percent)
        self.assertEqual(r.rows[0].availability_state, "OBSERVED_AVAILABLE_LOWER_BOUND")

    def test_fee_can_exist_with_missing_availability(self):
        r = validate_ibkr_usa_snapshot_v12(snapshot([row(fee="0.50", available="")]))
        self.assertEqual(r.rows[0].fee_rate_percent, "0.5")
        self.assertEqual(r.rows[0].availability_state, "MISSING")

    def test_zero_availability_is_observed_unavailable(self):
        r = validate_ibkr_usa_snapshot_v12(snapshot([row(fee="NA", available="0")]))
        self.assertEqual(r.observed_unavailable_rows, 1)
        self.assertEqual(r.availability_with_missing_fee_rows, 1)

    def test_blank_figi_allowed(self):
        r = validate_ibkr_usa_snapshot_v12(snapshot([row(figi="")]))
        self.assertIsNone(r.rows[0].figi)

    def test_available_na_fails_closed(self):
        with self.assertRaisesRegex(ValidationError, "AVAILABLE contains undocumented literal"):
            validate_ibkr_usa_snapshot_v12(snapshot([row(available="NA")]))

    def test_n_slash_a_fee_fails_closed(self):
        with self.assertRaisesRegex(ValidationError, "FEERATE contains undocumented"):
            validate_ibkr_usa_snapshot_v12(snapshot([row(fee="N/A")]))

    def test_duplicate_con_fails_closed(self):
        with self.assertRaisesRegex(ValidationError, "duplicate CON"):
            validate_ibkr_usa_snapshot_v12(snapshot([row(con=1001), row(sym="BBB", con=1001)]))

    def test_wrong_eof_count_fails_closed(self):
        with self.assertRaisesRegex(ValidationError, "#EOF row count"):
            validate_ibkr_usa_snapshot_v12(snapshot([row()], eof_count=2))

    def test_legacy_header_not_silently_accepted(self):
        legacy_header = "#SYM|CUR|NAME|CON|ISIN|REBATERATE|FEERATE|AVAILABLE|"
        legacy_row = "AAA|USD|Example Corp|1001|US0378331005|0.25|1.25|100|"
        with self.assertRaisesRegex(ValidationError, "header differs"):
            validate_ibkr_usa_snapshot_v12(snapshot([legacy_row], header=legacy_header))


if __name__ == "__main__":
    unittest.main()
