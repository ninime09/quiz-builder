"""Extract per-page text from (deduped) lecture PDFs into .txt files.

Each output file carries `===== PAGE N =====` markers so the page number can be
cited as the `source` of every quiz question (e.g. "M1 课件 P16"). Read these
.txt files when authoring questions — never guess page numbers.

Usage:
    python extract_text.py INPUT.pdf [INPUT2.pdf ...] [--out DIR]
    python extract_text.py --glob "week*/module*_dedup.pdf" --out _module_text

Default --out is "_module_text" under the current directory.
Requires: pip install pymupdf
"""
import argparse
import glob as globlib
from pathlib import Path

import fitz  # pymupdf


def extract(pdf: Path, out_dir: Path) -> Path:
    doc = fitz.open(pdf)
    out = out_dir / (pdf.stem + ".txt")
    with open(out, "w", encoding="utf-8") as f:
        for i, pg in enumerate(doc):
            f.write(f"\n===== PAGE {i + 1} =====\n")
            f.write(pg.get_text("text"))
    doc.close()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("inputs", nargs="*", help="PDF files to extract")
    ap.add_argument("--glob", help="glob pattern for inputs")
    ap.add_argument("--out", default="_module_text", help="output dir (default: _module_text)")
    args = ap.parse_args()

    inputs = list(args.inputs)
    if args.glob:
        inputs += globlib.glob(args.glob)
    if not inputs:
        ap.error("no input PDFs (pass paths or --glob)")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    for raw in inputs:
        p = Path(raw)
        if not p.exists():
            print(f"MISSING: {p}")
            continue
        out = extract(p, out_dir)
        print(f"{p.name} -> {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
