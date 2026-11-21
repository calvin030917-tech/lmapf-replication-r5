"""Figures for the public-layout validation, based on the saved counts."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import ListedColormap
from matplotlib.patches import Rectangle, Patch
import numpy as np

from warehouse import load_map

ROOT=Path(__file__).resolve().parent


def draw(language,folder,font):
    cn=language=="cn"
    def s(a,b):
        return a if cn else b
    if font and cn:
        font_manager.fontManager.addfont(font)
    family=(font_manager.FontProperties(fname=font).get_name() if font else "Noto Sans CJK SC") if cn else "DejaVu Sans"
    plt.rcParams.update({"font.family":family,"font.size":9,"axes.unicode_minus":False,"svg.fonttype":"path"})
    blue,red,ink,gray,grid="#24758A","#AB5133","#172D3B","#52707B","#E2EBEE"
    data=json.loads((ROOT/"data_r5/r5_summary.json").read_text())
    folder.mkdir(parents=True,exist_ok=True)

    def save(fig,name):
        for ext in ("png","pdf","svg"):
            fig.savefig(folder/f"{name}.{ext}",dpi=425,facecolor="white")
        plt.close(fig)

    fig,ax=plt.subplots(1,2,figsize=(7.55,2.72))
    fig.subplots_adjust(left=.045,right=.987,bottom=.24,top=.82,wspace=.12)
    for i,(a,m) in enumerate(zip(ax,("w1","w2"))):
        b=load_map(m)
        im=np.zeros((b.height,b.width),dtype=int)
        for p in b.cells:
            x,y=b.xy[p]
            im[y,x]=1
        for j,pool in enumerate(b.pools):
            for p in pool:
                x,y=b.xy[p]
                im[y,x]=2+j
        a.imshow(im,interpolation="nearest",origin="upper",
                 cmap=ListedColormap([ink,"#F6F9F9","#1C8C9E","#D7754F"]),vmin=0,vmax=3)
        ys=[b.xy[v][1] for pool in b.pools for v in pool]
        a.add_patch(Rectangle((b.width//2-13,min(ys)-2),26,max(ys)-min(ys)+4,
                              fill=False,color=red,linewidth=1,linestyle=(0,(4,2))))
        a.set_title(f"({chr(97+i)}) {m.upper()} · {b.width} × {b.height}",loc="left",color=ink,fontweight="bold")
        a.set_xticks([0,40,80,120,160])
        a.set_yticks([0,20,40,60,80] if m=="w2" else [0,20,40,60])
        a.set_xlim(-.5,b.width-.5);a.set_ylim(b.height-.5,-.5)
        a.tick_params(labelsize=7.7,length=2,color=gray,labelcolor=gray)
        for spine in a.spines.values():spine.set_color(grid)
    fig.legend(handles=[Patch(color=ink,label=s("货架及隔墙","Obstacles")),
                        Patch(color="#F6F9F9",ec=grid,label=s("可通行格","Aisles")),
                        Patch(color="#1C8C9E",label=s("上侧任务池","Upper goal pool")),
                        Patch(color="#D7754F",label=s("下侧任务池","Lower goal pool"))],
               ncol=4,loc="lower center",bbox_to_anchor=(.5,.035),frameon=False,handlelength=1.1)
    save(fig,"public_layout")

    fig,(a,b)=plt.subplots(1,2,figsize=(7.55,3.13),gridspec_kw={"width_ratios":[1.03,1.02]})
    fig.subplots_adjust(left=.18,right=.982,bottom=.22,top=.82,wspace=.42)
    proxies=data["proxies"]
    names=[s("首步方向","First direction"),s("两步进展","Two-step progress")]
    for i,k in enumerate(("proposed_direction","proposed_distance")):
        r=proxies[k]
        a.barh(i,r["tp"],color=blue,height=.48)
        a.barh(i,r["fn"],left=r["tp"],color="#B8D4DD",height=.48)
        a.text(r["tp"]+r["fn"]+.6,i,f"{r['tp']}/{r['tp']+r['fn']}",va="center",color=ink,fontsize=8.6)
    a.set_title(s("(a) 识别到的提前完工","(a) Detected focal gains"),loc="left",color=ink,fontweight="bold")
    a.set_xlabel(s("实测提前完工的配对数","Pairs with earlier completion"),color=gray)
    a.set_yticks(range(2),names)
    a.set_xlim(0,49)
    a.invert_yaxis()
    a.legend(handles=[Patch(color=blue,label=s("命中","Detected")),Patch(color="#B8D4DD",label=s("漏判","Missed"))],
               loc="upper left",bbox_to_anchor=(-.01,-.33),ncol=2,frameon=False,fontsize=8)
    flags=list(data["probes_verified"])
    values=[data["probes_verified"][k]["positive"] for k in flags]
    y=list(range(len(flags)))
    b.barh(y,values,color=[blue,red,"#678773","#8A749B"],height=.53)
    b.set_yticks(y,[s("预算","Budget"),s("预留","Reservations"),s("终点","Goal rule"),s("窗口","Window")])
    b.set_title(s("(b) 经参照核验的查询","(b) Verified query flags"),loc="left",color=ink,fontweight="bold")
    b.set_xlabel(s("查询阳性数","Positive queries"),color=gray)
    b.set_xlim(0,210)
    b.invert_yaxis()
    for i,v in enumerate(values):b.text(v+3,i,str(v),va="center",color=ink,fontsize=8.6)
    for z in (a,b):
        for k in ("top","left","right"):z.spines[k].set_visible(False)
        z.spines["bottom"].set_color(grid)
        z.set_axisbelow(True)
        z.grid(axis="x",color=grid,linewidth=.7)
        z.tick_params(axis="both",length=0,labelsize=8.3,labelcolor=ink)
    save(fig,"diagnostic_validation")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--language",choices=("cn","en"),required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--font")
    args=p.parse_args()
    draw(args.language,args.out,args.font)
