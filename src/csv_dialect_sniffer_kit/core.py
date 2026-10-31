"""Deterministic CSV dialect detection.

The standard library's :class:`csv.Sniffer` guesses a dialect by picking the
first delimiter that appears in a sample.  That is fast but unstable: a single
stray comma inside a quoted field, or a comment line, can flip the answer.  This
module instead scores each candidate by how consistently it splits every row
into the same number of columns, which is the property a CSV dialect actually
has.  Ties are broken by a fixed candidate order so the result is reproducible.

Only the standard library is used.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

# Candidate delimiters.  Order matters: when two candidates score equally we
# return the earlier one, which makes the result deterministic.
_DELIMITERS: Tuple[str, ...] = (",", "\t", ";", "|")

# Candidate quote characters.  We do not consider the empty string because a
# quoted CSV field is always wrapped in a character.
_QUOTES: Tuple[str, ...] = ('"', "'")


def _sample_lines(sample: str) -> List[str]:
    """Return the non-empty lines of *sample*.

    Blank lines carry no delimiter information and would otherwise count as a
    row with one column, which distorts the consistency score.
    """
    return [line for line in sample.splitlines() if line.strip()]


def _score_delimiter(lines: Sequence[str], delimiter: str, quotechar: str) -> float:
    """Score *delimiter* by the fraction of rows that agree on a column count.

    We parse with the real :mod:`csv` reader so that quoted fields containing
    the delimiter are handled correctly.  The score is the proportion of rows
    that share the most common column count.  A delimiter that never appears
    produces a single column for every row and therefore scores 1.0 as well;
    the tie-break in :func:`sniff` prefers the earlier candidate, and the
    candidate list is ordered by how common the delimiter is in practice.
    """
    if not lines:
        return 0.0
    try:
        reader = csv.reader(
            io.StringIO("\n".join(lines)),
            delimiter=delimiter,
            quotechar=quotechar,
            strict=False,
        )
        counts = [len(row) for row in reader]
    except csv.Error:
        return 0.0
    if not counts:
        return 0.0
    # The most common column count.  ``max`` with a key returns the first
    # maximum, so ties are resolved by the order the counts appear, which is
    # deterministic for a given input.
    best = max(set(counts), key=counts.count)
    return counts.count(best) / len(counts)


@dataclass(frozen=True)
class Dialect:
    """A detected CSV dialect.

    Attributes mirror the subset of :class:`csv.Dialect` that this module
    actually determines.  ``escapechar`` is ``None`` unless the sample contains
    a backslash, because we do not want to invent an escape character that the
    data never uses.
    """

    delimiter: str
    quotechar: str
    escapechar: Optional[str] = None

    def to_csv_dialect(self) -> csv.Dialect:
        """Return a :class:`csv.Dialect` instance for use with :mod:`csv`.

        This is a convenience for callers that want to hand the result straight
        to :func:`csv.reader` or :func:`csv.writer`.
        """
        return _DialectAdapter(self.delimiter, self.quotechar, self.escapechar)


class _DialectAdapter(csv.Dialect):
    """Concrete :class:`csv.Dialect` built from a :class:`Dialect`.

    :class:`csv.Dialect` is an abstract base class; instantiating it directly
    leaves the reader without the attributes it expects.  This adapter fills in
    sensible defaults for everything the detector does not decide.
    """

    def __init__(self, delimiter: str, quotechar: str, escapechar: Optional[str]) -> None:
        self.delimiter = delimiter
        self.quotechar = quotechar
        self.escapechar = escapechar
        self.doublequote = True
        self.skipinitialspace = False
        self.lineterminator = "\r\n"
        self.quoting = csv.QUOTE_MINIMAL


def sniff(sample: str) -> Dialect:
    """Detect the dialect of *sample*.

    The algorithm is:

    1. Split the sample into non-empty lines.
    2. For each candidate delimiter, parse the sample with each candidate quote
       character and score the delimiter by how many rows agree on a column
       count.
    3. Pick the highest scoring ``(delimiter, quotechar)`` pair.  Ties are
       broken by the order of the candidate lists, so the result is stable.

    Raises :class:`ValueError` if *sample* contains no non-empty lines.
    """
    lines = _sample_lines(sample)
    if not lines:
        raise ValueError("sample contains no non-empty lines")

    best_score = -1.0
    best_delimiter = _DELIMITERS[0]
    best_quote = _QUOTES[0]

    for delimiter in _DELIMITERS:
        for quotechar in _QUOTES:
            score = _score_delimiter(lines, delimiter, quotechar)
            # A delimiter that never appears splits every row into one column,
            # which also scores 1.0.  Such a degenerate score carries no
            # information, so only let it win when no candidate has actually
            # split the sample into multiple columns.
            if score == 1.0:
                separator = csv.reader(
                    io.StringIO("\n".join(lines)),
                    delimiter=delimiter,
                    quotechar=quotechar,
                    strict=False,
                )
                if not any(len(row) > 1 for row in separator):
                    score = 0.0
            # Strict greater-than keeps the first candidate on a tie, which is
            # what makes the result deterministic.
            if score > best_score:
                best_score = score
                best_delimiter = delimiter
                best_quote = quotechar

    # A backslash is the only escape character we can detect without guessing:
    # if the sample contains one, assume the dialect uses it.  Otherwise leave
    # it unset so the reader treats backslashes literally.
    escapechar: Optional[str] = "\\" if "\\" in sample else None

    return Dialect(delimiter=best_delimiter, quotechar=best_quote, escapechar=escapechar)
