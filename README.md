# csv-dialect-sniffer-kit

Detects a CSV dialect (delimiter, quote character, escape character) from a
sample string, deterministically and without third-party dependencies.

```python
import csv
import io

from csv_dialect_sniffer_kit import sniff

sample = 'name,age\n"Doe, Jane",42\n'
dialect = sniff(sample)
print(dialect.delimiter)   # ','
print(dialect.quotechar)   # '"'
print(dialect.escapechar)  # None

reader = csv.reader(io.StringIO(sample), dialect.to_csv_dialect())
```

The exported names are `sniff` and `Dialect`.  `sniff(sample)` returns a
`Dialect` with `delimiter`, `quotechar`, and `escapechar` attributes, plus a
`to_csv_dialect()` method that returns a concrete `csv.Dialect` suitable for
`csv.reader` and `csv.writer`.

## Why this exists

The standard library's `csv.Sniffer` picks the first delimiter it sees in the
sample.  A single comma inside a quoted field, or a comment line, can flip the
answer.  This library instead scores each candidate delimiter by the fraction
of rows that agree on a column count, which is the property a real CSV dialect
has.  The trade-off is that the detector needs at least two rows to be
meaningful; a single-row sample has no consistency to measure, and the first
candidate (comma) wins.  That is a deliberate choice: a deterministic answer is
more useful than a clever guess that changes between runs.

## The awkward edge

A sample with no delimiter at all (a single column of data) scores every
candidate equally.  The detector returns comma in that case, because comma is
the first candidate in the fixed order.  If your data is single-column and you
care about the exact delimiter, pass a sample that actually contains one.
