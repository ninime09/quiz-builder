"""Deduplicate PowerPoint-style animation builds in lecture PDFs.

Lecture slides exported to PDF often contain "build" animations: N consecutive
pages where each is a strict superset of the previous (bullets revealed one by
one). For quiz/cheatsheet authoring we only want the FINAL frame of each build,
otherwise the same slide's text is read 4-5 times.

Heuristic: page i is dropped if its normalized token multiset is an (almost)
subset of page i+1's. Keep the last page of each build sequence.

Usage:
    python dedup_pdf.py INPUT.pdf [INPUT2.pdf ...]
    python dedup_pdf.py --glob "week*/module*.pdf"   # shell-expanded is fine too

For each INPUT.pdf writes INPUT_dedup.pdf next to it and prints the page ratio.
Requires: pip install pymupdf
"""
import argparse
import glob as globlib
import re
from collections import Counter
from pathlib import Path

import fitz  # pymupdf


def normalize(text: str) -> list:
    """Tokenize + lowercase; drop pure-whitespace and 1-char tokens."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if len(t) > 1]


def is_subset(a: list, b: list, tolerance: int = 2) -> bool:
    """True if multiset(a) is (almost) a subset of multiset(b).

    `tolerance` allows up to N tokens of `a` to be missing from `b` — absorbs
    OCR noise / equation-render jitter on otherwise-identical pages.
    """
    ca, cb = Counter(a), Counter(b)
    missing = 0
    for tok, cnt in ca.items():
        diff = cnt - cb.get(tok, 0)
        if diff > 0:
            missing += diff
            if missing > tolerance:
                return False
    return True


def dedup_pdf(input_path: Path, output_path: Path) -> tuple:
    """Dedupe build animations. Returns (original_pages, kept_pages)."""
    doc = fitz.open(input_path)
    n = len(doc)
    page_tokens = [normalize(doc[i].get_text("text")) for i in range(n)]

    keep = [True] * n
    for i in range(n - 1):
        # Don't collapse near-empty title/divider pages onto the next.
        if len(page_tokens[i]) < 5:
            continue
        if is_subset(page_tokens[i], page_tokens[i + 1]):
            keep[i] = False

    out = fitz.open()
    for i in range(n):
        if keep[i]:
            out.insert_pdf(doc, from_page=i, to_page=i)
    out.save(output_path, deflate=True, garbage=4)
    out.close()
    doc.close()
    return n, sum(keep)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("inputs", nargs="*", help="PDF files to dedupe")
    ap.add_argument("--glob", help="glob pattern for inputs (e.g. 'week*/module*.pdf')")
    args = ap.parse_args()

    inputs = list(args.inputs)
    if args.glob:
        inputs += globlib.glob(args.glob)
    if not inputs:
        ap.error("no input PDFs (pass paths or --glob)")

    for raw in inputs:
        p = Path(raw)
        if not p.exists():
            print(f"MISSING: {p}")
            continue
        if p.stem.endswith("_dedup"):
            continue
        out = p.with_name(p.stem + "_dedup.pdf")
        orig, kept = dedup_pdf(p, out)
        print(f"{p.name}: {orig} -> {kept} pages ({kept / orig * 100:.0f}% kept)  -> {out.name}")


if __name__ == "__main__":
    main()
