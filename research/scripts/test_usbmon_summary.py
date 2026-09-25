import unittest

from usbmon_summary import parse_bulk_line, summarize


class UsbmonTextTest(unittest.TestCase):
    def test_decodes_documented_bulk_submission(self):
        line = ("dd65f0e8 4128379752 S Bo:1:005:2 -115 31 = "
                "55534243 ad000000 00800000 80010a28 20000000 20000040 00000000 000000")
        event = parse_bulk_line(line)
        self.assertEqual((event.bus, event.device, event.endpoint, event.direction), (1, 5, 2, "out"))
        self.assertEqual(event.declared_length, 31)
        self.assertEqual(len(event.payload), 31)
        self.assertFalse(event.truncated)

    def test_marks_payload_omission_and_truncation(self):
        omitted = parse_bulk_line("abc 100 C Bi:2:004:1 0 64 >")
        truncated = parse_bulk_line("def 110 C Bi:2:004:1 0 64 = 01020304")
        self.assertIsNone(omitted.payload)
        self.assertTrue(truncated.truncated)
        result = summarize([omitted, truncated])
        self.assertEqual(result["events"], 2)
        self.assertEqual(result["payloadOmitted"], 1)
        self.assertEqual(result["payloadTruncated"], 1)

    def test_rejects_nonbulk_or_malformed_data_without_guessing(self):
        self.assertIsNone(parse_bulk_line("abc 100 S Ci:1:001:0 s a3 00 0000 0003 0004 4 <"))
        self.assertIsNone(parse_bulk_line("not a usbmon line"))
        self.assertIsNone(parse_bulk_line("def 110 C Bi:2:004:1 0 4 = badhex"))


if __name__ == "__main__":
    unittest.main()
