"""Deep inspection of what a buyer receives (owner, 10 Nov 2026: "check the actual documents ... give people value").

Unlike value_audit.py (which scores content volume), this looks for defects a buyer would notice:
  XLSX  error cells after a real recalculation, summaries/dashboards that show nothing with the example data,
        charts with no data behind them, sheets with almost nothing on them, how many example rows there are
  PDF   page count, near-empty pages, A4 and US Letter both present
  DOCX  words, tables, whether a worked example is included
  ALL   products whose text is nearly the same as another product's (the same thing sold twice)
Needs spreadsheets recalculated by LibreOffice first (pass the folder as argv[1]; files named <ID>__<name>.xlsx).
Writes docs/2.0/inspection.csv.
"""
import csv, glob, json, os, re, sys, warnings
from collections import defaultdict
import docx, openpyxl
from pypdf import PdfReader
warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECALC = sys.argv[1] if len(sys.argv) > 1 else None
ERR = re.compile(r"^#(REF!|DIV/0!|NAME\?|VALUE!|N/A|NUM!|NULL!)|^Err:\d+")
SKIP = {"start here", "guide", "lists", "how to use"}


def xlsx(pid, path):
    name = os.path.basename(path).replace(" ", "_")
    rc = os.path.join(RECALC, f"{pid}__{name}")
    wf = openpyxl.load_workbook(path)                      # formulas
    wv = openpyxl.load_workbook(rc, data_only=True)        # recalculated values
    out = {"sheets": len(wf.sheetnames), "errors": [], "dead": [], "thin": [], "formulas": 0, "example_rows": 0, "charts": 0, "empty_charts": 0, "text": []}
    for ws in wf.worksheets:
        vs = wv[ws.title] if ws.title in wv.sheetnames else None
        if vs is None: out["errors"].append(f"{ws.title}: sheet missing after recalc"); continue
        nf = nz = filled = 0; rows_with_input = set()
        for row in ws.iter_rows():
            for c in row:
                if c.value is None: continue
                filled += 1
                v = vs.cell(c.row, c.column).value
                if isinstance(c.value, str) and c.value.startswith("="):
                    nf += 1
                    if isinstance(v, str) and ERR.match(v): out["errors"].append(f"{ws.title}!{c.coordinate}: {v}")
                    elif v not in (None, "", 0): nz += 1
                else:
                    if isinstance(c.value, str): out["text"].append(c.value)
                    if c.row > 4 and not isinstance(c.value, str): rows_with_input.add(c.row)
        out["formulas"] += nf
        low = ws.title.lower()
        if low not in SKIP:
            out["example_rows"] += len(rows_with_input)
            if filled < 12: out["thin"].append(f"{ws.title} ({filled} cells)")
            if nf >= 4 and nz / nf < 0.15 and any(k in low for k in ("summary", "dashboard", "report", "overview", "results")):
                out["dead"].append(f"{ws.title} ({nz}/{nf} formulas show a value)")
        for ch in getattr(ws, "_charts", []):
            out["charts"] += 1
            try:
                refs = [s.val.numRef.f for s in ch.series if s.val is not None and s.val.numRef is not None]
                tot = 0
                for ref in refs:
                    sh, rng = ref.rsplit("!", 1); sh = sh.strip("'")
                    for r in wv[sh][rng.replace("$", "")]:
                        for c in (r if isinstance(r, tuple) else (r,)):
                            if isinstance(c.value, (int, float)) and c.value: tot += 1
                if refs and tot == 0: out["empty_charts"] += 1
            except Exception as e:
                pass
    return out


def pdf(path):
    r = PdfReader(path)
    pages = [(p.extract_text() or "") for p in r.pages]
    w = [len(t.split()) for t in pages]
    box = r.pages[0].mediabox
    return {"pages": len(pages), "words": sum(w), "near_empty": sum(1 for x in w if x < 4), "size": "A4" if abs(float(box.width) - 595) < 3 else "Letter" if abs(float(box.width) - 612) < 3 else f"{float(box.width):.0f}", "text": pages}


def docx_(path):
    d = docx.Document(path)
    paras = [p.text for p in d.paragraphs if p.text.strip()]
    cells = [c.text for t in d.tables for row in t.rows for c in row.cells if c.text.strip()]
    text = paras + cells
    return {"words": sum(len(t.split()) for t in text), "tables": len(d.tables), "placeholders": sum(len(re.findall(r"\[[^\]]{2,60}\]", t)) for t in text),
            "headings": sum(1 for p in d.paragraphs if p.style.name.lower().startswith("heading")), "text": text}


def shingles(text):
    w = re.findall(r"[a-z]{3,}", text.lower())
    return {" ".join(w[i:i + 4]) for i in range(len(w) - 3)}


def main():
    cat = json.load(open(os.path.join(ROOT, "catalogue", "products.json")))
    cat = cat if isinstance(cat, list) else cat.get("products", cat)
    meta = {p["id"]: p for p in cat}
    rows, sh = [], {}
    for d in sorted(glob.glob(os.path.join(ROOT, "build", "products", "*", "files"))):
        pid = d.split(os.sep)[-2]; m = meta.get(pid, {})
        r = {"id": pid, "name": m.get("name", ""), "price": m.get("price_zar", ""), "kind": "", "files": len(os.listdir(d)), "pages": 0, "words": 0, "sheets": 0, "formulas": 0,
             "example_rows": 0, "charts": 0, "worked_example": 0, "issues": []}
        text = []
        for f in sorted(os.listdir(d)):
            p = os.path.join(d, f); e = f.rsplit(".", 1)[-1].lower()
            r["kind"] = "+".join(sorted(set(filter(None, r["kind"].split("+"))) | {e}))
            if "worked example" in f.lower(): r["worked_example"] = 1
            try:
                if e == "xlsx":
                    x = xlsx(pid, p); text += x["text"]
                    for k in ("sheets", "formulas", "example_rows", "charts"): r[k] += x[k]
                    r["issues"] += [f"ERROR {x_}" for x_ in x["errors"][:5]] + [f"DEAD SUMMARY {x_}" for x_ in x["dead"]] + [f"THIN SHEET {x_}" for x_ in x["thin"]]
                    if x["empty_charts"]: r["issues"].append(f"EMPTY CHART x{x['empty_charts']}")
                    if len(x["errors"]) > 5: r["issues"].append(f"... {len(x['errors'])} error cells in total")
                elif e == "pdf":
                    x = pdf(p)
                    if "letter" not in f.lower() or r["pages"] == 0:
                        r["pages"] = x["pages"]; r["words"] += x["words"]; text += x["text"]
                    if x["near_empty"] > max(2, x["pages"] // 3): r["issues"].append(f"NEAR-EMPTY PAGES {x['near_empty']}/{x['pages']} in {f}")
                    r.setdefault("_sizes", set()).add(x["size"])
                elif e == "docx":
                    x = docx_(p); text += x["text"]; r["words"] += x["words"]
                    if x["words"] < 250: r["issues"].append(f"SHORT DOC {x['words']} words: {f}")
            except Exception as ex:
                r["issues"].append(f"CANNOT OPEN {f}: {type(ex).__name__} {str(ex)[:80]}")
        if "pdf" in r["kind"] and r.pop("_sizes", set()) != {"A4", "Letter"} and r["kind"] == "pdf": r["issues"].append("MISSING A4 or Letter version")
        r.pop("_sizes", None)
        sh[pid] = shingles(" ".join(text)); rows.append(r)
    ids = [r["id"] for r in rows]; by = {r["id"]: r for r in rows}
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            A, B = sh[a], sh[b]
            if len(A) > 40 and len(B) > 40:
                j = len(A & B) / len(A | B)
                if j > 0.7:
                    by[a]["issues"].append(f"NEAR-DUPLICATE of {b} ({j:.0%})"); by[b]["issues"].append(f"NEAR-DUPLICATE of {a} ({j:.0%})")
    with open(os.path.join(ROOT, "docs", "2.0", "inspection.csv"), "w", newline="") as f:
        w = csv.writer(f); cols = ["id", "name", "price", "kind", "files", "pages", "words", "sheets", "formulas", "example_rows", "charts", "worked_example", "issues"]
        w.writerow(cols)
        for r in rows: w.writerow([r[c] if c != "issues" else " | ".join(r["issues"]) for c in cols])
    bad = [r for r in rows if r["issues"]]
    print(f"{len(rows)} products inspected, {len(bad)} with findings")
    kinds = defaultdict(int)
    for r in bad:
        for i in r["issues"]: kinds[i.split(" ")[0] + " " + i.split(" ")[1] if i.split(" ")[0] in ("DEAD", "THIN", "EMPTY", "SHORT", "CANNOT", "MISSING") else i.split(" ")[0]] += 1
    print(dict(kinds))


if __name__ == "__main__":
    main()
