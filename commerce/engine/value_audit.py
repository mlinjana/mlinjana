"""Value audit: what is actually inside every product file, compared with its price.

Owner direction (7 Nov 2026): "if a product is expensive the product must be worth the money ... we can't give a weak
SOP template and expect a big payment; if need be we even give an example." This measures each product's real content,
so prices and upgrades are based on evidence rather than titles.

Measures (from build/products/<ID>/files):
  PDF   pages, words
  DOCX  words (paragraphs + tables), tables, worked-example signal (example/sample text with filled content)
  XLSX  sheets, distinct formula patterns (a formula copied down 3,000 rows counts once), charts, data validations,
        example data rows, instructions sheet
Content score -> a "fair ceiling" price for the product as it is today. Products priced above their ceiling are
flagged: either lower the price or upgrade the content.

Usage: python3 engine/value_audit.py  -> docs/2.0/value-audit.csv and a summary on stdout
"""
import csv, glob, json, os, re, sys
from collections import Counter

import docx
import openpyxl
from pypdf import PdfReader

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build", "products")
OUT = os.path.join(ROOT, "docs", "2.0", "value-audit.csv")
EXAMPLE_RE = re.compile(r"\b(example|sample|worked|e\.g\.|for instance|filled)\b", re.I)


def pdf_metrics(path):
    r = PdfReader(path)
    words = sum(len((pg.extract_text() or "").split()) for pg in r.pages)
    return {"pages": len(r.pages), "words": words}


def docx_metrics(path):
    d = docx.Document(path)
    para = [p.text for p in d.paragraphs]
    cells = [c.text for t in d.tables for row in t.rows for c in row.cells]
    text = "\n".join(para + cells)
    blank_cells = sum(1 for c in cells if not c.strip())
    return {"words": len(text.split()), "tables": len(d.tables), "examples": len(EXAMPLE_RE.findall(text)),
            "placeholder_brackets": len(re.findall(r"\[[^\]]{3,}\]", text)), "blank_cells": blank_cells}


def xlsx_metrics(path):
    wb = openpyxl.load_workbook(path)
    patterns, charts, dv, example_rows, has_help, words = set(), 0, 0, 0, False, 0
    for ws in wb.worksheets:
        if re.search(r"start|how|instructions|read", ws.title, re.I):
            has_help = True
        charts += len(ws._charts)
        dv += len(ws.data_validations.dataValidation)
        for row in ws.iter_rows():
            vals = [c.value for c in row]
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("="):
                    patterns.add(re.sub(r"\$?[A-Z]{1,3}\$?\d+", "R", c.value))  # same logic in another row = same pattern
                elif isinstance(c.value, str) and len(c.value.split()) >= 6:  # 2.0: guidance sentences (Start Here, Guide sheets, notes)
                    words += len(c.value.split())
            typed = [v for v in vals if v is not None and not (isinstance(v, str) and v.startswith("="))]
            if len(typed) >= 3 and row[0].row > 3:
                example_rows += 1
    return {"sheets": len(wb.worksheets), "formula_patterns": len(patterns), "charts": charts, "validations": dv,
            "data_rows": example_rows, "has_help": has_help, "words": words}


def score(m):
    """Content points; deliberately simple so the owner can follow it."""
    s = 0
    s += min(m.get("pages", 0), 40) * 0.6                      # printable pages
    s += min(m.get("words", 0), 6000) / 120                     # written guidance and examples
    s += min(m.get("formula_patterns", 0), 120) * 0.35          # real calculation logic
    s += m.get("charts", 0) * 2 + min(m.get("validations", 0), 10) * 0.5
    s += min(m.get("examples", 0), 20) * 0.5 + min(m.get("data_rows", 0), 60) * 0.08
    s += 3 if m.get("has_help") else 0
    s += max(m.get("sheets", 0) - 1, 0) * 1.5 + m.get("tables", 0) * 0.4
    return round(s, 1)


# score -> fair price ceiling today (rand); same ladder as the catalogue's price points
LADDER = [(0, 29), (12, 39), (20, 49), (28, 59), (36, 69), (45, 79), (55, 89), (65, 99), (80, 129), (100, 149), (130, 199)]


def ceiling(s):
    return [p for t, p in LADDER if s >= t][-1]


def main():
    cat = json.load(open(os.path.join(ROOT, "catalogue", "products.json")))["products"]
    by_slug = {p["slug"]: p for p in cat}
    rows = []
    for p in cat:
        fdir = os.path.join(BUILD, p["id"], "files")
        m = Counter()
        for f in glob.glob(os.path.join(fdir, "**", "*"), recursive=True):
            low = f.lower()
            try:
                part = pdf_metrics(f) if low.endswith(".pdf") else docx_metrics(f) if low.endswith(".docx") else \
                    xlsx_metrics(f) if low.endswith(".xlsx") else None
            except Exception as e:  # a broken file is itself a finding
                part = {"errors": 1}
                print("could not read", f, e, file=sys.stderr)
            if not part:
                continue
            if "Letter" in os.path.basename(f) and low.endswith(".pdf"):
                continue  # the US Letter copy repeats the A4 content
            for k, v in part.items():
                m[k] += int(v)
        bundle = bool(p.get("bundle_of"))
        if bundle:
            parts = [by_slug[s] for s in p["bundle_of"] if s in by_slug]
            fair = round(sum(r["price_zar"] for r in parts) * 0.65)  # bundles: judged against their parts
            s = None
        else:
            s = score(m)
            fair = ceiling(s)
        price = p["price_zar"]
        rows.append({"id": p["id"], "name": p["name"], "store": p["store"], "category": p["category"], "price_zar": price,
                     "score": s if s is not None else "", "fair_ceiling_zar": fair, "gap_zar": price - fair,
                     "verdict": "overpriced" if price > fair * 1.15 + 5 else "fair" if price >= fair * 0.7 else "underpriced",
                     **{k: m.get(k, 0) for k in ("pages", "words", "tables", "examples", "placeholder_brackets", "sheets",
                                                  "formula_patterns", "charts", "validations", "data_rows", "has_help")}})
    rows.sort(key=lambda r: -r["gap_zar"])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    v = Counter(r["verdict"] for r in rows)
    print(f"{len(rows)} products: {dict(v)}  -> {os.path.relpath(OUT, ROOT)}")
    print("Biggest gaps (price minus fair ceiling today):")
    for r in rows[:30]:
        print(f"  {r['id']:8} R{r['price_zar']:>4} fair≈R{r['fair_ceiling_zar']:>4} gap R{r['gap_zar']:>4}  score {r['score']!s:>5}  {r['name'][:55]}")


if __name__ == "__main__":
    main()
