import unittest

from csv_dialect_sniffer_kit import Dialect, sniff


class SniffTests(unittest.TestCase):
    def test_comma_delimited(self):
        sample = "a,b,c\n1,2,3\n4,5,6\n"
        dialect = sniff(sample)
        self.assertEqual(dialect.delimiter, ",")
        self.assertEqual(dialect.quotechar, '"')

    def test_tab_delimited(self):
        sample = "a\tb\tc\n1\t2\t3\n"
        dialect = sniff(sample)
        self.assertEqual(dialect.delimiter, "\t")

    def test_semicolon_delimited(self):
        sample = "a;b;c\n1;2;3\n"
        dialect = sniff(sample)
        self.assertEqual(dialect.delimiter, ";")

    def test_pipe_delimited(self):
        sample = "a|b|c\n1|2|3\n"
        dialect = sniff(sample)
        self.assertEqual(dialect.delimiter, "|")

    def test_quoted_field_containing_delimiter(self):
        sample = 'a,b\n"x,y",z\n'
        dialect = sniff(sample)
        self.assertEqual(dialect.delimiter, ",")

    def test_single_quote_character(self):
        sample = "a,b\n'x,y',z\n"
        dialect = sniff(sample)
        self.assertEqual(dialect.quotechar, "'")

    def test_escapechar_detected(self):
        sample = 'a,b\n"x\\"y",z\n'
        dialect = sniff(sample)
        self.assertEqual(dialect.escapechar, "\\")

    def test_escapechar_absent(self):
        sample = "a,b\n1,2\n"
        dialect = sniff(sample)
        self.assertIsNone(dialect.escapechar)

    def test_empty_sample_raises(self):
        with self.assertRaises(ValueError):
            sniff("")

    def test_blank_lines_ignored(self):
        sample = "\n\na,b\n1,2\n\n"
        dialect = sniff(sample)
        self.assertEqual(dialect.delimiter, ",")

    def test_to_csv_dialect_roundtrip(self):
        sample = "a;b\n1;2\n"
        dialect = sniff(sample)
        csv_dialect = dialect.to_csv_dialect()
        self.assertEqual(csv_dialect.delimiter, ";")
        self.assertEqual(csv_dialect.quotechar, '"')

    def test_deterministic_tie_break(self):
        # A single column of data has no delimiter; the first candidate wins.
        sample = "alpha\nbeta\ngamma\n"
        dialect = sniff(sample)
        self.assertEqual(dialect.delimiter, ",")


if __name__ == "__main__":
    unittest.main()
