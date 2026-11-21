"""Build the anonymous ICML layout from the full English R5 manuscript."""
from collections import defaultdict
from pathlib import Path
import re

from aligned_tables import build
from build_aligned_word import image_path
from build_cn import parse

HERE = Path(__file__).resolve().parent
SOURCES = (
    "stern2019", "ma2017", "li2021", "asano2023", "zheng2026", "phillips2011",
    "ma2019", "okumura2022", "klancar2026", "veerapaneni2025", "zhang2026dag",
    "liang2025", "morag2024", "chen2024", "zhang2024", "zang2025",
    "anand2026", "zhang2024queue", "movingai",
)
TEXT_REPLACEMENTS = {
    "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
    "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}", "<": r"\textless{}", ">": r"\textgreater{}",
    "−": r"\ensuremath{-}", "–": "--", "—": "---", "×": r"\ensuremath{\times}",
    "→": r"\ensuremath{\rightarrow}", "≥": r"\ensuremath{\geq}",
    "Δ": r"\ensuremath{\Delta}", "τ": r"\ensuremath{\tau}",
    "α": r"\ensuremath{\alpha}", "·": r"\textperiodcentered{}", "§": r"\S{}",
    "č": r"\v{c}", "…": r"\ldots{}",
}
CITATION = re.compile(r"\[(\d+(?:[–,]\d+)*(?:, §\d+)?)\]")
DISPLAY = re.compile(r"\b(?:Table|Figure) (?:[ABC]\d+|\d+[AB]?)\b")
DEFERRED = {"4.1", "4.2", "5.2", "5.4"}
MAIN_DISPLAYS = {"proxy", "diagnostic_validation"}


def literal(text):
    for old, new in (("dₜ", r"d_t"), ("Dᵢ", r"D_i")):
        text = text.replace(old, f"☉{new}☽")
    pieces = re.split(r"(☉[^☽]*☽)", text)
    return "".join(
        "$" + piece[1:-1] + "$" if piece.startswith("☉")
        else "".join(TEXT_REPLACEMENTS.get(char, char) for char in piece)
        for piece in pieces
    )


def paragraph(text):
    def cite(match):
        numbers, marker, section = match[1].partition(", §")
        keys = []
        for piece in numbers.split(","):
            first, separator, last = piece.partition("–")
            end = int(last) if separator else int(first)
            keys.extend(SOURCES[i - 1] for i in range(int(first), end + 1))
        locator = rf"[Sec.~{section}]" if marker else ""
        return rf"\citep{locator}{{{','.join(keys)}}}"

    def link_displays(prose):
        spans = DISPLAY.split(prose)
        links = [
            rf"\hyperlink{{{display_anchor(match[0])}}}{{{literal(match[0])}}}"
            for match in DISPLAY.finditer(prose)
        ]
        return "".join(literal(span) + link for span, link in zip(spans, links + [""]))

    parts = []
    start = 0
    for match in CITATION.finditer(text):
        parts += [link_displays(text[start:match.start()]), cite(match)]
        start = match.end()
    return "".join(parts) + link_displays(text[start:])


def display_anchor(text):
    return "display:" + text.split(".", 1)[0].replace(" ", "")


def table(data):
    title, headers, rows, widths, note, _ = data
    widths = [width / sum(widths) for width in widths]
    cols = "@{}" + "".join(
        rf">{{\raggedright\arraybackslash}}p{{\dimexpr{w:.5f}\linewidth-{2 * w * (len(widths) - 1):.5f}\tabcolsep\relax}}"
        for w in widths
    ) + "@{}"
    entries = [
        " & ".join(r"\textbf{" + literal(head.replace("\n", " ")) + "}" for head in headers) + r" \\",
        r"\midrule",
    ]
    for row in rows:
        cells = [literal(str(cell).replace("\n", " ")) for cell in row]
        study = re.match(r"^\[(\d+)\] ", str(row[0]))
        if study and title.startswith("Table 1."):
            cells[0] = rf"\citet{{{SOURCES[int(study[1]) - 1]}}}"
        entries.append(" & ".join(cells) + r" \\")
    return "\n".join([
        r"\par\medskip\noindent\begin{minipage}{\linewidth}",
        rf"\small\hypertarget{{{display_anchor(title)}}}{{}}\textbf{{" + literal(title) + r"}\par\smallskip",
        r"\setlength{\tabcolsep}{4pt}\renewcommand{\arraystretch}{1.12}",
        r"\begin{tabular}{" + cols + "}",
        r"\toprule", *entries, r"\bottomrule", r"\end{tabular}",
        r"\par\smallskip " + literal(note) if note else "",
        r"\end{minipage}\par\medskip",
    ])


def figure(key, caption):
    asset = image_path(key)
    if key in {"diagnostic_validation", "public_layout"}:
        asset = asset.with_suffix(".pdf")
    path = Path("..") / asset.relative_to(HERE.parent)
    return "\n".join([
        r"\par\medskip\noindent\begin{minipage}{\linewidth}\centering",
        rf"\hypertarget{{{display_anchor(caption)}}}{{}}%",
        rf"\includegraphics[width=\linewidth,height=.44\textheight,keepaspectratio]{{{path.as_posix()}}}\par",
        r"\small\smallskip " + literal(caption),
        r"\end{minipage}\par\medskip",
    ])


ALGORITHM = r"""
\par\medskip\noindent\begin{minipage}{\columnwidth}
\small\textbf{Algorithm 1. Plan and execute one round from a snapshot}\par\smallskip
\textbf{Input} Snapshot $S$, issued goals, tested order $\pi$, window $W$, and node cap $B$.
\begin{enumerate}\setlength{\itemsep}{1pt}\setlength{\parsep}{0pt}\setlength{\topsep}{3pt}
\item Build shared safe paths $P[1\ldots N]$. Reserve cells and reverse edges. Set $b=B$.
\item For each robot $i$ in $\pi$, remove $P[i]$ from the reservation table and log the other paths.
\item Query goal or window paths with cap $b$. Debit expanded nonterminal states.
\item Replace $P[i]$ if a candidate is returned. Otherwise retain $P[i]$.
\item Restore the occupancy and reverse edges of $P[i]$ in the table.
\item Check safety and execute two actions. Record completion and issue the next goal after each step.
\end{enumerate}
\end{minipage}\par\medskip
"""

PREAMBLE = r"""\documentclass{article}
\usepackage{microtype}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{array}
\usepackage{amsmath,amssymb}
\usepackage{hyperref}
\usepackage{icml2027}
\hypersetup{pdfauthor={},pdftitle={Diagnosing Single-Robot Priority Promotion in Lifelong Warehouse Path Finding}}
\icmltitlerunning{Diagnosing Single-Robot Priority Promotion}
\begin{document}
"""


def build_tex():
    rows = parse(HERE / "paper_en.txt")
    tables = build()
    front = {row[0]: row[1] for row in rows[:4]}
    paper = [
        PREAMBLE, r"\twocolumn[",
        r"\icmltitle{" + literal(front["TITLE"]) + r"\texorpdfstring{\\{\large " + literal(front["SUB"]) + "}}{}}",
        r"\begin{icmlauthorlist}\icmlauthor{Anonymous Authors}{anon}\end{icmlauthorlist}",
        r"\icmlaffiliation{anon}{Anonymous Institution}",
        r"\icmlkeywords{" + literal(front["KEY"]) + "}",
        r"\vskip 0.25in]", r"\printAffiliationsAndNotice{}",
        r"\begin{abstract}", paragraph(front["ABSTRACT"]), r"\end{abstract}",
    ]
    appendix, supplements = [], defaultdict(list)
    current = ""
    in_appendix = False
    for kind, *values in rows[4:]:
        value = values[0] if values else ""
        if kind == "H1":
            current = value.split(" ", 1)[0]
            if value.startswith("Appendix "):
                if not in_appendix:
                    appendix.append(r"\clearpage\onecolumn\appendix\raggedbottom")
                    in_appendix = True
                heading = value.split(". ", 1)[1]
                if value.startswith("Appendix B."):
                    appendix.append(r"\clearpage")
                appendix.append(r"\section{" + literal(heading) + "}")
            elif current.isdigit():
                paper.append(r"\section{" + literal(value.split(" ", 1)[1]) + "}")
            else:
                if value == "Reproducibility Materials":
                    paper.append(r"\label{end:main}")
                paper.append(r"\section*{" + literal(value) + "}")
        elif kind == "H2":
            current, heading = value.split(" ", 1)
            paper.append(r"\subsection{" + literal(heading) + "}")
            if current in DEFERRED:
                paper.append(rf"The full text and associated displays are in \hyperlink{{sup:{current}}}{{Appendix D, Section {current}}}." + "\n")
            supplements[current].append(
                r"\subsection*{Section " + current + r"\quad " + literal(heading) + "}"
                + rf"\hypertarget{{sup:{current}}}{{}}"
            )
        elif kind == "REFS":
            paper.extend([
                r"\section*{Impact Statement}",
                "Measuring realized service alongside search can help identify when a local scheduling decision delays other robots. The experiments use generated demand and discrete warehouse motion. Deployment requires validation of local safety and operational constraints.",
                r"\bibliographystyle{icml2027}",
                r"\bibliography{references}",
            ])
        elif kind == "P":
            destination = appendix if in_appendix else supplements[current] if current in DEFERRED else paper
            destination.extend([paragraph(value), ""])
        elif kind in {"TABLE", "FIG"}:
            block = table(tables[value]) if kind == "TABLE" else figure(value, values[1])
            if value in MAIN_DISPLAYS:
                paper.extend([r"\begin{figure*}[t]", block, r"\end{figure*}"])
            else:
                destination = appendix if in_appendix else supplements[current]
                destination.append(block)
        elif kind == "EQ":
            paper.extend([r"\begin{equation}", r"F_\tau=\frac{D_1+\cdots+D_N}{NT}.", r"\end{equation}"])
        elif kind == "ALGO":
            paper.append(ALGORITHM)
        else:
            raise ValueError(kind)
    appendix.extend([
        r"\clearpage\section{Supplementary Methods, Results, and Displays}\label{app:supp}",
        "The sections below retain their manuscript numbers so that the methods, results, and displays can be matched to the main text.",
    ])
    for blocks in supplements.values():
        if len(blocks) > 1:
            appendix.extend(blocks)
    paper.extend(appendix)
    return "\n".join(paper + [r"\end{document}", ""])


if __name__ == "__main__":
    (HERE / "lmapf_r5.tex").write_text(build_tex(), encoding="utf-8")
