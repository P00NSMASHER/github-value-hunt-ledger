import json
import unittest

import import_registries as reg


class HospitalRegistryImportTests(unittest.TestCase):
    def test_parse_roster_omits_phone_values(self):
        raw = json.dumps([
            {
                "ccn": "123456",
                "name": "Example Hospital",
                "address": "1 Main St",
                "city": "Example",
                "state": "PA",
                "zip": "12345",
                "phone": "hpt-obf:v1:should-not-survive",
                "type": "Acute Care Hospitals",
            }
        ]).encode()
        parsed = reg.parse_roster(raw)
        self.assertEqual(parsed["123456"]["name"], "Example Hospital")
        self.assertEqual(parsed["123456"]["address"], "1 Main St")
        self.assertNotIn("phone", parsed["123456"])

    def test_assessable_boolean_is_fail_closed(self):
        self.assertEqual(reg.as_bool("yes"), 1)
        self.assertEqual(reg.as_bool("NO"), 0)
        self.assertIsNone(reg.as_bool(""))
        self.assertIsNone(reg.as_bool("unknown"))
        self.assertIsNone(reg.as_bool(None))

    def test_raw_urls_are_pinned_to_revision(self):
        url = reg.raw_github_url("owner/repo", "deadbeef", "data/file.csv")
        self.assertEqual(
            url,
            "https://raw.githubusercontent.com/owner/repo/deadbeef/data/file.csv",
        )

    def test_csv_parser_handles_quoted_commas(self):
        rows = reg.parse_csv(
            b'ccn,hospital_name,evidence\n'
            b'123456,"Example, Hospital","cms-hpt.txt found, file opened"\n'
        )
        self.assertEqual(rows[0]["hospital_name"], "Example, Hospital")
        self.assertEqual(rows[0]["evidence"], "cms-hpt.txt found, file opened")


if __name__ == "__main__":
    unittest.main()
