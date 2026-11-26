"""Convert the built article (paper/main.tex) to a Word file for the authors to rewrite.

Plain-language summary: resolves citations to author-year text, converts figures to PNG,
runs pandoc, then formats the Word file (Times New Roman 12 pt, double spacing, page
numbers, table borders). With --compare OLD.tex, every sentence that does not appear in
OLD.tex is highlighted yellow, so the authors can see what is new.

Usage: python tools/paper_to_docx.py OUT.docx [--compare OLD.tex]
"""
import argparse, os, re, subprocess, tempfile
from docx import Document
from docx.enum.text import WD_COLOR_INDEX, WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def cite_map(tex):
    m = {}
    for lab, key in re.findall(r"\\bibitem\[(.+?)\]\{(.+?)\}", tex):
        mm = re.match(r"(.*)\((.*?)\)$", lab.strip())
        m[key] = (mm.group(1).strip(), mm.group(2)) if mm else (lab, "")
    return m


def resolve_cites(tex):
    m = cite_map(tex)
    def p(x):
        ks = [k.strip() for k in x.group(2).split(",")]
        if x.group(1) == "t":
            return "; ".join(f"{m[k][0]} ({m[k][1]})" for k in ks)
        return "(" + "; ".join(f"{m[k][0]}, {m[k][1]}" for k in ks) + ")"
    return re.sub(r"\\cite(p|t)\{(.+?)\}", p, tex)


SUP = {"2": "\u00b2", "*": "*", "**": "**", "***": "***"}
SUB = {"1": "\u2081", "2": "\u2082"}


def math_to_text(tex):
    """Inline math in this paper is simple; render it as Unicode text so Word shows it."""
    def conv(m):
        t = m.group(1)
        for a, b in (("\\chi", "\u03c7"), ("\\rho", "\u03c1"), ("\\times", "\u00d7"), ("\\leq", "\u2264"),
                     ("\\geq", "\u2265"), ("\\le", "\u2264"), ("\\ge", "\u2265"), ("{,}", ","), ("\\,", " ")):
            t = t.replace(a, b)
        t = re.sub(r"\^\{?(\*+|2)\}?", lambda x: SUP[x.group(1)], t)
        t = re.sub(r"_\{?([12])\}?", lambda x: SUB[x.group(1)], t)
        t = re.sub(r"-(?=\d)", "\u2212", t)
        return t.replace("{", "").replace("}", "")
    return re.sub(r"(?<!\\)\$(.+?)(?<!\\)\$", conv, tex)


def prep(tex_path, work):
    tex = open(tex_path, encoding="utf-8").read()
    tex = resolve_cites(tex)
    tex = math_to_text(tex)
    aux = os.path.join(work, "labels", "main.aux")
    if os.path.abspath(tex_path) == os.path.join(ROOT, "paper", "main.tex") and not os.path.exists(aux):
        os.makedirs(os.path.dirname(aux), exist_ok=True)
        subprocess.run(["pdflatex", "-interaction=batchmode", "-output-directory", os.path.dirname(aux), "main.tex"],
                       cwd=os.path.dirname(tex_path), capture_output=True)
    labels = dict(re.findall(r"\\newlabel\{(.+?)\}\{\{(.*?)\}", open(aux).read())) if os.path.exists(aux) else {}
    tex = re.sub(r"\\ref\{(.+?)\}", lambda m: labels.get(m.group(1), ""), tex)
    figdir = os.path.join(os.path.dirname(tex_path), "figures")
    def fig(mo):
        src = os.path.join(figdir, os.path.basename(mo.group(2)))
        if not os.path.exists(src):
            src = os.path.join(ROOT, "paper", "figures", os.path.basename(mo.group(2)))
        stem = os.path.join(work, os.path.splitext(os.path.basename(src))[0])
        if os.path.exists(src) and not os.path.exists(stem + ".png"):
            subprocess.run(["pdftoppm", "-png", "-r", "200", "-singlefile", src, stem], check=True)
        return f"\\includegraphics[{mo.group(1)}]{{{stem}.png}}"
    tex = re.sub(r"\\includegraphics\[(.*?)\]\{(.+?)\}", fig, tex)
    tex = re.sub(r"\\linenumbers|\\usepackage(\[.*?\])?\{lineno\}", "", tex)
    out = os.path.join(work, "in.tex")
    open(out, "w", encoding="utf-8").write(tex)
    return out


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z(])|\n", text) if s.strip()]


def norm(s):
    s = re.sub(r"(Section|Table|Figure)\s*\d*", r"\1 ", s)  # cross-reference numbers differ between builds
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def to_text(tex_path, work):
    """Text of an article rendered through the same pandoc path as the Word file."""
    out = os.path.join(work, "old.docx")
    subprocess.run(["pandoc", prep(tex_path, work), "-o", out, "--resource-path", work], check=True)
    d = Document(out)
    lines = [p.text for p in d.paragraphs]
    lines += [c.text for t in d.tables for r in t.rows for c in r.cells]
    return "\n".join(lines)


def borders(table):
    tblPr = table._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{side}")
        for k, v in (("val", "single"), ("sz", "4"), ("space", "0"), ("color", "000000")):
            e.set(qn(f"w:{k}"), v)
        b.append(e)
    tblPr.append(b)


def page_numbers(doc):
    for s in doc.sections:
        p = s.footer.paragraphs[0] if s.footer.paragraphs else s.footer.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run()
        for t, txt in (("begin", None), (None, "PAGE"), ("end", None)):
            if t:
                f = OxmlElement("w:fldChar"); f.set(qn("w:fldCharType"), t); r._r.append(f)
            else:
                i = OxmlElement("w:instrText"); i.text = txt; r._r.append(i)


def highlight_new(doc, old_sents):
    """Highlight every run that falls inside a sentence not found in the old text."""
    n = 0
    def para(p):
        nonlocal n
        runs = [r for r in p.runs]
        txt = "".join(r.text for r in runs)
        if not txt.strip():
            return
        spans, pos = [], 0
        for s in sentences(txt):
            k = txt.find(s, pos)
            if k < 0:
                continue
            pos = k + len(s)
            if norm(s) and f" {norm(s)} " not in old_sents:
                spans.append((k, pos)); n += 1
        if not spans:
            return
        off = 0
        for r in runs:
            a, b = off, off + len(r.text); off = b
            if r.text.strip() and any(a < e and b > s0 for s0, e in spans):
                r.font.highlight_color = WD_COLOR_INDEX.YELLOW
    for p in doc.paragraphs:
        para(p)
    for t in doc.tables:
        for row in t.rows:
            for c in row.cells:
                for p in c.paragraphs:
                    para(p)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--compare")
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as work:
        src = prep(os.path.join(ROOT, "paper", "main.tex"), work)
        subprocess.run(["pandoc", src, "-o", a.out, "--resource-path", work], check=True)
        doc = Document(a.out)
        for st in doc.styles:
            try:
                st.font.name = "Times New Roman"
                st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
            except Exception:
                pass
        doc.styles["Normal"].font.size = Pt(12)
        for p in doc.paragraphs:
            p.paragraph_format.line_spacing = 2.0
        for t in doc.tables:
            borders(t)
        page_numbers(doc)
        if a.compare:
            old = " " + " ".join(norm(ln) for ln in to_text(a.compare, work).splitlines()) + " "
            print("highlighted:", highlight_new(doc, old))
        doc.save(a.out)
    print("written", a.out)


if __name__ == "__main__":
    main()
