"""Render the section-for-section English R5 Word manuscript."""
import argparse
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

from aligned_tables import ROOT, build
from build_cn import algorithm, equation, link, oxml, parse, style, table

HERE = Path(__file__).resolve().parent
REST = ROOT / "manuscript_cn"
NEW_FIGURES = {"public_layout", "diagnostic_validation"}


def image_path(key):
    folder = ROOT / "figures_r5/en" if key in NEW_FIGURES else ROOT / "historical_r4/figures_en"
    return folder / f"{key}.png"


def refs():
    lines = [line.split("|", 2)[1:] for line in (REST/"refs.txt").read_text(encoding="utf-8").splitlines() if line.strip()]
    order = (1,2,3,4,13,5,6,7,8,9,16,17,10,11,18,12,14,15,19)
    return [lines[i-1] for i in order]


def make(path):
    doc = Document()
    for paragraph_style in doc.styles:
        for border in paragraph_style.element.xpath("./w:pPr/w:pBdr"):
            border.getparent().remove(border)
    sec = doc.sections[0]
    sec.page_width = Inches(8.27)
    sec.page_height = Inches(11.69)
    sec.top_margin = Inches(.72)
    sec.bottom_margin = Inches(.69)
    sec.left_margin = sec.right_margin = Inches(.785)
    sec.footer_distance = Inches(.31)
    style(doc,"Normal",10.8,14.3,6)
    style(doc,"Title",21.5,26,6,bold=True,sans=True).paragraph_format.keep_with_next=True
    style(doc,"Subtitle",11.1,15,14,sans=True).paragraph_format.keep_with_next=True
    for tag,pt,leading,after,before in (("Heading 1",15,21,5,13),("Heading 2",12,17,3,9)):
        style(doc,tag,pt,leading,after,before,bold=True,sans=True).paragraph_format.keep_with_next=True
    style(doc,"Front",10.5,15.3,8)
    style(doc,"Table Caption",9.6,13.5,4,6,bold=True,sans=True)
    style(doc,"Table Text",8.8,11.3,0)
    style(doc,"Table Note",8.6,11,7,3)
    style(doc,"Figure Caption",9.1,11.5,8,3)
    style(doc,"Figure",9,10,0,0)
    style(doc,"Equation",11,29,4)
    style(doc,"Algorithm",9.3,12,2)
    style(doc,"Reference",9.0,11.6,3)
    style(doc,"Footer",8,10,0)
    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer._p.append(oxml("w:fldSimple", w_instr="PAGE"))
    props = doc.core_properties
    props.author = ""
    props.last_modified_by = ""
    props.comments = ""
    props.subject = "Lifelong multi-agent path finding"
    props.keywords = "LMAPF, warehouse, paired replanning"
    tables = build()
    for row in parse(HERE/"paper_en.txt"):
        kind = row[0]
        value = row[1] if len(row)>1 else ""
        if kind in ("TITLE","SUB"):
            p=doc.add_paragraph(value, "Title" if kind=="TITLE" else "Subtitle")
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            if kind == "TITLE":
                props.title=value
        elif kind in ("ABSTRACT","KEY"):
            p=doc.add_paragraph(style="Front")
            p.add_run("Abstract  " if kind=="ABSTRACT" else "Keywords  ").bold=True
            p.add_run(value)
        elif kind in ("H1","H2"):
            p=doc.add_paragraph(value,"Heading 1" if kind=="H1" else "Heading 2")
            if value.startswith(("Appendix A.","Appendix B.")):
                p.paragraph_format.page_break_before=True
        elif kind=="P":
            doc.add_paragraph(value)
        elif kind=="TABLE":
            table(doc,tables[value],False)
        elif kind=="FIG":
            p=doc.add_paragraph(style="Figure")
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.line_spacing=1.0
            p.paragraph_format.keep_with_next=True
            img=p.add_run().add_picture(str(image_path(value)),width=Inches(6.68))
            img._inline.docPr.set("descr",row[2])
            p=doc.add_paragraph(row[2],"Figure Caption")
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.keep_together=True
        elif kind=="EQ":
            equation(doc)
        elif kind=="ALGO":
            algorithm(doc,False)
        elif kind=="REFS":
            doc.add_paragraph("References","Heading 1")
            for index,(entry,url) in enumerate(refs(),1):
                p=doc.add_paragraph(style="Reference")
                p.paragraph_format.left_indent=Pt(21)
                p.paragraph_format.first_line_indent=Pt(-21)
                p.add_run(f"[{index}] "+entry.split("] ",1)[1]+"  ")
                label="DOI "+url.split("doi.org/")[-1] if "doi.org" in url else "Source"
                link(p,label,url)
        else:
            raise ValueError(kind)
    path.parent.mkdir(parents=True,exist_ok=True)
    doc.save(path)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    make(args.out/"LMAPF_Literature_Review_EN_R5.docx")
