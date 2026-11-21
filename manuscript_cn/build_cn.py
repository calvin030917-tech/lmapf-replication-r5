"""Build the two language versions of the journal-style manuscript."""

import argparse
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.shared import Inches, Pt, RGBColor

from tables_cn import build_tables

ROOT = Path(__file__).resolve().parent
REPRO = ROOT.parent/"historical_r4"
FIGURE_WIDTH = 6.68


def oxml(name, *children, **attrs):
    element = OxmlElement(name)
    for child in children:
        element.append(child)
    for attr, value in attrs.items():
        element.set(qn(attr.replace("_",":")),str(value))
    return element


def style(doc, name, point, lines, after, before=0, bold=False, sans=False, indent=0):
    s = doc.styles[name] if name in doc.styles else doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
    s.font.name = "Times New Roman"
    s.font.size = Pt(point)
    s.font.bold = bold
    s.font.italic = False
    s.font.color.rgb = RGBColor.from_string("171F25")
    font=s.element.get_or_add_rPr().get_or_add_rFonts()
    for key in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
        font.attrib.pop(qn("w:"+key),None)
    font.set(qn("w:eastAsia"),"Noto Sans CJK SC" if sans else "Noto Serif CJK SC")
    f=s.paragraph_format
    f.line_spacing=Pt(lines)
    f.space_after=Pt(after)
    f.space_before=Pt(before)
    f.first_line_indent=Pt(indent)
    f.widow_control=True
    return s


def link(p, name, url):
    item=oxml("w:hyperlink",r_id=p.part.relate_to(url,RELATIONSHIP_TYPE.HYPERLINK,is_external=True))
    txt=oxml("w:t")
    txt.text=name
    item.append(oxml("w:r",oxml("w:rPr",oxml("w:color",w_val="245678")),txt))
    p._p.append(item)


def table(doc, spec, cn):
    title, header, rows, widths, note, custom_size=spec
    p=doc.add_paragraph(title,"Table Caption")
    p.paragraph_format.keep_with_next=True
    t=doc.add_table(rows=0,cols=len(header))
    t.alignment=WD_TABLE_ALIGNMENT.CENTER
    t.autofit=False
    for col,w in zip(t.columns,widths):
        col.width=Inches(w)
    row_margin=40 if "原文定位" in title or "source locations" in title else 61
    for ri,row in enumerate([header]+rows):
        cells=t.add_row()
        props=cells._tr.get_or_add_trPr()
        props.append(oxml("w:cantSplit"))
        if not ri:
            props.append(oxml("w:tblHeader"))
        for col,(value,w,c) in enumerate(zip(row,widths,cells.cells)):
            c.width=Inches(w)
            c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            b=oxml("w:tcBorders",oxml("w:bottom",w_val="single",w_sz="5" if ri==len(rows) else "3",
                                      w_color="AEBCC4" if ri==len(rows) else "D7E0E4"))
            if not ri:
                b.append(oxml("w:top",w_val="single",w_sz="7",w_color="879CA8"))
            pr=c._tc.get_or_add_tcPr()
            pr.append(b)
            margin=oxml("w:tcMar")
            for edge,value_dxa in (("top",row_margin),("left",78),("bottom",row_margin),("right",78)):
                margin.append(oxml("w:"+edge,w_w=value_dxa,w_type="dxa"))
            pr.append(margin)
            if not ri:
                pr.append(oxml("w:shd",w_fill="EAF0F4"))
            p=c.paragraphs[0]
            p.style=doc.styles["Table Text"]
            p.paragraph_format.keep_with_next=not ri or (ri==len(rows) and bool(note))
            if col and len(header)>4:
                p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            else:
                p.alignment=WD_ALIGN_PARAGRAPH.LEFT
            run=p.add_run(str(value))
            run.bold=not ri
            if custom_size is not None:
                run.font.size=Pt(custom_size)
    if note:
        p=doc.add_paragraph(note,"Table Note")
        p.paragraph_format.keep_together=True
    else:
        p=doc.add_paragraph()
        p.paragraph_format.line_spacing=Pt(3)
        p.paragraph_format.space_after=Pt(2)


def equation(doc):
    def mr(value):
        txt=oxml("m:t")
        txt.set(qn("xml:space"),"preserve")
        txt.text=value
        return oxml("m:r",txt)
    def sub(v,i):
        return oxml("m:sSub",oxml("m:e",mr(v)),oxml("m:sub",mr(i)))
    numerator=oxml("m:num",sub("D","1"),mr(" + ⋯ + "),sub("D","N"))
    denominator=oxml("m:den",mr("NT"))
    p=doc.add_paragraph(style="Equation")
    p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p._p.append(oxml("m:oMath",sub("F","τ"),mr(" = "),oxml("m:f",numerator,denominator)))
    p.add_run("     (1)")


def algorithm(doc, cn):
    if cn:
        caption="算法 1　从快照规划并执行一轮"
        rows=[
            "输入  快照 S、当前目标、待测次序 π、窗口 W、每轮上限 B",
            "1   为所有车辆构造共同安全种子 P[1…N]，建立格占用与反向边预留，令余额 b=B。",
            "2   对 π 中每辆车 i，先从预留表移除 P[i]，记录其余车辆的全部路径。",
            "3       在剩余 b 内查询便于执行的时空窗路径。扣除非终止状态的实际展开数。",
            "4       若返回到达或窗口候选，则替换 P[i]。否则沿用 P[i]。",
            "5       将 P[i] 的格和反向边放回预留表。",
            "6   检查联合窗口，无冲突则执行头两步。逐步登记完工并发出下一目标。"
        ]
    else:
        caption="Algorithm 1. Plan and execute one round from a snapshot"
        rows=[
            "Input  Snapshot S, issued goals, tested order π, window W, and node cap B",
            "1   Build shared safe paths P[1…N]. Reserve cells and reverse edges. Set b = B.",
            "2   For each robot i in π, remove P[i] from the reservation table and log the other paths.",
            "3       Query goal or window paths with cap b. Debit expanded nonterminal states.",
            "4       Replace P[i] if a candidate is returned. Otherwise retain P[i].",
            "5       Restore the occupancy and reverse edges of P[i] in the table.",
            "6   Check safety and execute two actions. Record completion and issue the next goal after each step."
        ]
    doc.add_paragraph(caption,"Table Caption").paragraph_format.keep_with_next=True
    for i,line in enumerate(rows):
        p=doc.add_paragraph(line,"Algorithm")
        p.paragraph_format.keep_with_next=i<len(rows)-1
        p.paragraph_format.space_after=Pt(7 if i==len(rows)-1 else 2)
        p.add_run()
    return


def parse(path):
    return [line.split("|",2) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def make(lang, path):
    cn=lang=="cn"
    doc=Document()
    for paragraph_style in doc.styles:
        borders=paragraph_style.element.xpath("./w:pPr/w:pBdr")
        for border in borders:
            border.getparent().remove(border)
    sec=doc.sections[0]
    sec.page_width=Inches(8.27)
    sec.page_height=Inches(11.69)
    sec.top_margin=Inches(.72)
    sec.bottom_margin=Inches(.69)
    sec.left_margin=sec.right_margin=Inches(.785)
    sec.footer_distance=Inches(.31)
    style(doc,"Normal",10.6 if cn else 10.8,16 if cn else 14.3,6,indent=20 if cn else 0)
    style(doc,"Title",21 if cn else 21.5,29 if cn else 26,6,bold=True,sans=True).paragraph_format.keep_with_next=True
    style(doc,"Subtitle",10.6 if cn else 11.1,15,14,sans=True).paragraph_format.keep_with_next=True
    h1=style(doc,"Heading 1",15,21,5,13,bold=True,sans=True)
    h2=style(doc,"Heading 2",12,17,3,9,bold=True,sans=True)
    h1.paragraph_format.keep_with_next=h2.paragraph_format.keep_with_next=True
    style(doc,"Front",10.5,15.3,8)
    style(doc,"Secondary Title",12,16,4,8,bold=True).paragraph_format.keep_with_next=True
    style(doc,"Secondary Front",9.5,12.5,6)
    style(doc,"Table Caption",9.6,13.5,4,6,bold=True,sans=True)
    style(doc,"Table Text",9.0 if cn else 8.8,12.8 if cn else 11.3,0)
    style(doc,"Table Note",8.6,12 if cn else 11,7,3)
    style(doc,"Figure Caption",9.1,13 if cn else 11.5,8,3)
    style(doc,"Figure",9,10,0,0)
    style(doc,"Equation",11,29,4)
    style(doc,"Algorithm",9.3,13.3 if cn else 12,2)
    style(doc,"Reference",9.0,11.6,3)
    style(doc,"Footer",8,10,0)
    footer=sec.footer.paragraphs[0]
    footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
    footer._p.append(oxml("w:fldSimple",w_instr="PAGE"))
    props=doc.core_properties
    props.author=""
    props.last_modified_by=""
    props.subject="Lifelong multi-agent path finding"
    props.keywords="LMAPF, warehouse, paired replanning"
    props.comments=""
    figure_dir=REPRO/("figures" if cn else "figures_en")
    tables=build_tables(lang)

    references=[line.split("|",2)[1:] for line in (ROOT/"refs.txt").read_text(encoding="utf-8").splitlines() if line.strip()]
    ref_order=(1,2,3,4,13,5,6,7,8,9,16,17,10,11,18,12,14,15,19)
    first=[references[i-1] for i in ref_order]
    for item in parse(ROOT/f"paper_{lang}.txt"):
        kind=item[0]
        value=item[1] if len(item)>1 else None
        if kind in ("TITLE","SUB"):
            p=doc.add_paragraph(value,"Title" if kind=="TITLE" else "Subtitle")
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            if kind=="TITLE":
                props.title=value
        elif kind in ("ABSTRACT","KEY"):
            label=("摘要　" if cn else "Abstract  ") if kind=="ABSTRACT" else ("关键词　" if cn else "Keywords  ")
            p=doc.add_paragraph(style="Front")
            p.add_run(label).bold=True
            p.add_run(value)
        elif kind in ("EN_TITLE","EN_ABS","EN_KEY"):
            p=doc.add_paragraph(style="Secondary Title" if kind=="EN_TITLE" else "Secondary Front")
            if kind=="EN_TITLE":
                p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            else:
                p.add_run("Abstract  " if kind=="EN_ABS" else "Keywords  ").bold=True
            p.add_run(value)
        elif kind in ("H1","H2"):
            p=doc.add_paragraph(value,"Heading 1" if kind=="H1" else "Heading 2")
            if value.startswith(("附录 A","附录 B","Appendix B.")):
                p.paragraph_format.page_break_before=True
        elif kind=="P":
            p=doc.add_paragraph(value)
            if value.endswith("图1说明相同吞吐量下逐车负担可以不同。") or value.endswith("Figure 1 illustrates unequal exposure at equal throughput."):
                p.paragraph_format.keep_with_next=True
        elif kind=="TABLE":
            table(doc,tables[value],cn)
        elif kind=="FIG":
            p=doc.add_paragraph(style="Figure")
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.line_spacing=1.0
            p.paragraph_format.keep_with_next=True
            asset = ROOT.parent/"figures_r5"/"cn"/f"{value}.png" if value in ("public_layout","diagnostic_validation") else figure_dir/f"{value}.png"
            img=p.add_run().add_picture(str(asset),width=Inches(FIGURE_WIDTH))
            img._inline.docPr.set("descr",item[2])
            p=doc.add_paragraph(item[2],"Figure Caption")
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.keep_together=True
        elif kind=="EQ":
            equation(doc)
        elif kind=="ALGO":
            algorithm(doc,cn)
        elif kind=="REFS":
            doc.add_paragraph("参考文献" if cn else "References","Heading 1")
            for num,(entry,url) in enumerate(first,1):
                p=doc.add_paragraph(style="Reference")
                f=p.paragraph_format
                f.left_indent=Pt(21)
                f.first_line_indent=Pt(-21)
                p.add_run(f"[{num}] "+entry.split("] ",1)[1]+"  ")
                label="DOI "+url.split("doi.org/")[-1] if "doi.org" in url else ("原文" if cn else "Paper")
                link(p,label,url)
        else:
            raise ValueError(kind)
    path.parent.mkdir(parents=True,exist_ok=True)
    doc.save(path)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,required=True)
    out=parser.parse_args().out
    make("cn",out/"LMAPF_Literature_Review_CN_R5.docx")
