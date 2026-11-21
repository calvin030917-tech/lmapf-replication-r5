"""Regenerate publication figures from explicit scenarios and replay data."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Patch
from matplotlib.lines import Line2D

import argparse
import json
import os
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.patches import Rectangle
from simulator import layout
from figure_labels import ENGLISH
from protocol import strata, EXEC, LOOK

parser=argparse.ArgumentParser()
parser.add_argument('--out',type=Path,default=Path('figures'))
parser.add_argument('--data',type=Path,default=Path('data'))
parser.add_argument('--font',default=os.environ.get('LMAPF_CJK_FONT'))
parser.add_argument('--lang',choices=('cn','en'),default='cn')
args=parser.parse_args()

def tr(label):
    return ENGLISH[label] if args.lang=='en' else label
folder=args.out
folder.mkdir(parents=True,exist_ok=True)
if args.font:
    font_manager.fontManager.addfont(args.font)
    family=font_manager.FontProperties(fname=args.font).get_name()
    bold_font = Path(args.font).with_name(Path(args.font).name.replace("Regular", "Bold"))
    if bold_font != Path(args.font) and bold_font.exists():
        font_manager.fontManager.addfont(bold_font)
elif args.lang=='en':
    family='DejaVu Sans'
else:
    family=['Noto Sans CJK SC','Source Han Sans SC','Microsoft YaHei','PingFang SC','Arial Unicode MS']
plt.rcParams.update({'font.family':family,'font.size':9,'svg.fonttype':'path','axes.unicode_minus':False})
navy='#1A2E43'; blue='#2B678D'; light='#DCEBF3'; orange='#B4512D'; sunset='#F5D9CD'; grey='#526575'; grid='#DBE2E9'
def export(fig,name):
    fig.savefig(folder/f'{name}.png',dpi=600,facecolor='white')
    fig.savefig(folder/f'{name}.svg',facecolor='white')
    plt.close(fig)

fig,axes=plt.subplots(1,2,figsize=(7.35,2.63))
fig.subplots_adjust(left=.073,right=.994,bottom=.265,top=.79,wspace=.28)
datasets=[([(0,4,True),(4,8,True),(8,12,False)],[(0,4,True),(4,8,True),(8,12,False)]),
          ([(0,3,True),(3,6,True),(6,9,True),(9,12,True)],[(0,12,False)])]
for j,ax in enumerate(axes):
    ax.set_xlim(0,12.4);ax.set_ylim(-.37,1.55);ax.set_xticks(range(0,13,2));ax.set_yticks([0,1],[tr('车辆 B'),tr('车辆 A')])
    ax.tick_params(length=0,axis='both',labelsize=8.5,colors=grey)
    for sp in ax.spines.values():sp.set_visible(False)
    ax.set_axisbelow(True);ax.grid(axis='x',linewidth=.55,color=grid)
    a,b=datasets[j]
    for y,series in [(1,a),(0,b)]:
        for start,end,completed in series:
            length=min(4,end-start);startshow=start+.05
            ax.barh(y,max(length-.075,0),left=startshow,height=.34,color=light,edgecolor=blue,linewidth=.75,zorder=3)
            if end-start>4:
                ax.barh(y,end-start-4-.045,left=start+4,height=.34,color=sunset,edgecolor=orange,linewidth=.75,hatch='///',zorder=3)
            if completed:ax.plot(end,y,'o',ms=4.5,color=navy,markeredgecolor='white',markeredgewidth=.5,zorder=4)
    ax.set_xlabel(tr('仿真时间（步）'),color=navy,fontsize=8.5,labelpad=3)
    ax.set_title([tr('(a) 两车均完成任务'),tr('(b) 完成量集中于车辆 A')][j],loc='left',color=navy,fontweight='bold',pad=11,fontsize=10 if args.lang=='en' else 11)
    ax.text(.0,1.005,[tr('完成 4 项  /  超龄车步 0 / 24'),tr('完成 4 项  /  超龄车步 8 / 24')][j],transform=ax.transAxes,color=grey,fontsize=8.2)
fig.legend(handles=[Patch(facecolor=light,edgecolor=blue,label=tr('未超过时限的任务步')),Patch(facecolor=sunset,edgecolor=orange,hatch='///',label=tr('超过时限的任务步')),Line2D([0],[0],marker='o',markersize=4,linestyle='None',color=navy,label=tr('任务完成'))],loc='lower center',bbox_to_anchor=(.52,.018),ncol=3,frameon=False,fontsize=8.5,handlelength=1.6,columnspacing=1.8)
export(fig,'fig1')

fig,ax=plt.subplots(figsize=(7.35,2.87))
fig.subplots_adjust(left=.015,right=.985,top=.975,bottom=.045)
ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis('off')
def card(x,y,w,h,title,sub,fc,ec):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.006,rounding_size=0.019',facecolor=fc,edgecolor=ec,linewidth=1))
    ax.text(x+w/2,y+h*.67,title,ha='center',va='center',color=navy,fontsize=10.0 if args.lang=='en' else 10.7,fontweight='bold')
    ax.text(x+w/2,y+h*.30,sub,ha='center',va='center',color=grey,fontsize=8.55)
def arrow(x1,y1,x2,y2):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='-|>',mutation_scale=9,color=grey,linewidth=.9,shrinkA=0,shrinkB=0))
card(.22,.765,.56,.192,tr('同一拥堵时刻'),tr('复制位置、任务、公共预留与节点预算'),'#F5F7F9',grid)
arrow(.43,.764,.242,.638);arrow(.57,.764,.758,.638)
card(.015,.435,.455,.19,tr('(a) 原顺序'),tr('按原定优先级规划'),'#F2F7FA',blue)
card(.53,.435,.455,.19,tr('(b) 仅将焦点车移至队首'),tr('其余车辆保留相对顺序'),'#FAF2ED',orange)
arrow(.242,.433,.414,.285);arrow(.758,.433,.586,.285)
card(.105,.040,.79,.23,tr('记录执行前缀与后续通行'),tr('搜索启动、首段动作、32 步内的出区及多车完工'),'#F5F7F9',grid)
export(fig,'fig2')
from corridor_figure import make_corridor_figure
make_corridor_figure(plt, export, navy, blue, light, orange, sunset, grey, grid, tr)

fig, axs = plt.subplots(1, 2, figsize=(7.35, 2.70))
fig.subplots_adjust(left=.055, right=.990, top=.89, bottom=.25, wspace=.12)
colors = ["#26394A","#FFFFFF","#E5EFF3","#F5DCCF"]
for j, (ax, name) in enumerate(zip(axs, ("single","bypass"))):
    g = layout(name)
    img = np.zeros((g.height,g.width))
    depot = set(g.depots[0]+g.depots[1])
    for k in g.cells:
        x,y = g.xy[k]
        img[y,x] = 2 if k in depot else 3 if g.bank(k)==0 else 1
    ax.imshow(img,cmap=ListedColormap(colors),vmin=0,vmax=3,origin='upper',interpolation='none')
    ax.set_xticks(np.arange(-.5,g.width,1),minor=True)
    ax.set_yticks(np.arange(-.5,g.height,1),minor=True)
    ax.grid(which='minor',color='#C5D0D8',lw=.35)
    ax.add_patch(Rectangle((6.5,-.5),3,11,fill=False,edgecolor=orange,
                           lw=1,ls=(0,(4,2)),clip_on=False))
    ax.set_xticks([0,4,7,9,12,16])
    ax.set_yticks([0,5,10] if j==0 else [])
    ax.tick_params(which='both',length=0,colors=grey,labelsize=8)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title([tr('(a) 单中央通道'),tr('(b) 带旁路的中央通道')][j],loc='left',
                 color=navy,fontweight='bold',fontsize=10.9,pad=6)
handles = [Patch(facecolor=fc,edgecolor=navy if idx==1 else fc,linewidth=.55,label=lab)
           for idx,(fc,lab) in enumerate(zip(colors,[tr('货架或隔墙'),tr('车道'),tr('可分配目标'),tr('瓶颈带内可通行格')]))]
fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.52,.025),
           ncol=4,frameon=False,fontsize=8.15,handlelength=1.3)
export(fig,'fig4')

data=json.loads((args.data/'results.json').read_text())
A,B,C=(data['examples'][t] for t in "ABC")
affected = max((j for j in C['others_later']
                if all(C[b]['task'][j] is not None for b in ('baseline','treatment'))),
               key=lambda j:C['task_delta'][j])
examples = [
    (A,A["focus"],tr('(a) 搜索启动但动作相同'),
     f"新增 {A['treatment']['solver'][A['focus']]['expanded']} 次展开；两分支均第 {A['baseline']['gate'][A['focus']]} 步出区"),
    (B,B["focus"],tr('(b) 动作改变但完成变晚'),
     f"完工由第 {B['baseline']['task'][B['focus']]} 步延至第 {B['treatment']['task'][B['focus']]} 步"),
    (C,C["focus"],tr('(c) 焦点车提早出区'),
     f"出区 {C['baseline']['gate'][C['focus']]} → {C['treatment']['gate'][C['focus']]} 步；完工 {C['baseline']['task'][C['focus']]} → {C['treatment']['task'][C['focus']]} 步"),
    (C,affected,f"{tr('(d) 同一干预下的车辆')} {affected}",
     f"出区均为第 {C['baseline']['gate'][affected]} 步；完工 {C['baseline']['task'][affected]} → {C['treatment']['task'][affected]} 步"),
]
fig,axs=plt.subplots(2,2,figsize=(7.35,4.16))
fig.subplots_adjust(left=.097,right=.98,top=.84,bottom=.158,wspace=.31,hspace=.86)
for ax,(q,i,title,sub) in zip(axs.flat,examples):
    d=layout(q['layout']).distance[q['goals'][i]]
    ax.axvspan(0,EXEC,color='#ECF0F3',zorder=0)
    ax.axhline(0,color='#B8C7D0',lw=.6)
    for b,c,ls in [('baseline',blue,'-'),('treatment',orange,(0,(4,2)))]:
        out=q[b]
        path=out['path'][i]
        done=out['task'][i]
        stop=LOOK if done is None else done
        vals = [d[v] for v in path[:stop+1]]
        ax.step(range(stop+1),vals,where='post',color=c,lw=1.55,ls=ls)
        if done is not None:
            ax.plot(done,0,marker='o',markersize=4,color=c,zorder=5,markeredgecolor='white',mew=.38)
    for sp in ('top','right'):
        ax.spines[sp].set_visible(False)
    for sp in ('left','bottom'):
        ax.spines[sp].set_color('#B8C7D0')
    ax.grid(axis='y',color='#E1E8EC',linewidth=.50)
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=8,colors=grey,length=2.3)
    ax.set_xlim(0,32.4)
    ax.set_xticks([0,8,16,24,32])
    ax.set_title(title,loc='left',color=navy,fontweight='bold',fontsize=10.4,pad=16)
    if args.lang == 'en':
        orig, new = q['baseline'], q['treatment']
        if q is A:
            sub = f"8 new expansions; exit at step {orig['gate'][i]} in both arms"
        elif q is B:
            sub = f"Completion: {orig['task'][i]} → {new['task'][i]} steps"
        elif i == C["focus"]:
            sub = f"Exit: {orig['gate'][i]} → {new['gate'][i]}; completion: {orig['task'][i]} → {new['task'][i]}"
        else:
            sub = f"Exit unchanged; completion: {orig['task'][i]} → {new['task'][i]}"
    ax.text(0,1.020,sub,transform=ax.transAxes,color=grey,fontsize=8.0)
fig.text(.018,.53,tr('距当前目标的静态步数'),rotation=90,va='center',color=navy,fontsize=8.8)
fig.text(.53,.093,tr('快照后的时间（步）'),ha='center',color=navy,fontsize=8.8)
fig.legend(handles=[Line2D([0],[0],color=blue,lw=1.6,label=tr('原顺序')),
                    Line2D([0],[0],color=orange,ls='--',lw=1.6,label=tr('单次提权')),
                    Patch(facecolor='#ECF0F3',edgecolor='#D8E2E8',label=tr('首段执行')),
                    Line2D([0],[0],color=navy,marker='o',ls='None',ms=4,label=tr('当前任务完成'))],
           loc='lower center',bbox_to_anchor=(.53,.013),
           ncol=4,frameon=False,fontsize=8.4)
export(fig,'fig5')

fig,axs=plt.subplots(1,2,figsize=(7.35,3.77),sharey=True)
fig.subplots_adjust(left=.260 if args.lang=="en" else .225,right=.978,top=.858,bottom=.185,wspace=.15)
labs=[]
for ix,cell in enumerate(strata()):
    mode,n,b=cell
    title = tr('单中央通道') if mode=='single' else tr('旁路')
    labs.append(f"{title} · {n}{tr('车')} · {b*n}{tr('节点')}")
    for j,ctrl in enumerate(('congestion','relative')):
        p=next(z for z in data['contrasts']
               if (z['layout'],z['n'],z['multiplier'])==cell and z['control']==ctrl)
        p0,pp=p['f3_pp'],p['f3_ci']
        p1,qq=100*p['rate_ratio'],[100*x for x in p['ratio_ci']]
        alt=blue if j==0 else orange
        mark='o' if j==0 else 'D'
        y=ix+(-.16 if j==0 else .16)
        for k,(a,bound) in enumerate(((p0,pp),(p1,qq))):
            axs[k].hlines(y,bound[0],bound[1],color=alt,lw=1.2,zorder=3)
            axs[k].plot(a,y,marker=mark,ms=3.7,color=alt,mew=.35,mec='white',ls='none',zorder=4)
for ax in axs:
    ax.set_ylim(7.64,-.64)
    for p in (0,2,4,6):
        ax.axhspan(p-.5,p+.5,color='#F1F5F7',zorder=0)
    for s in ('top','left','right'):
        ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_color('#B8C7D0')
    ax.grid(axis='x',color='#D9E2E8',linewidth=.5)
    ax.tick_params(axis='x',labelsize=8,length=2,color='#A9BCC6',labelcolor=grey)
    ax.tick_params(axis='y',length=0,labelsize=8,labelcolor=navy)
    ax.set_axisbelow(True)
axs[0].set_yticks(range(len(labs)),labs)
axs[0].axvline(0,color=grey,lw=.7)
axs[1].axvline(100,color=grey,lw=.7)
axs[1].axvline(95,color=grey,lw=.9,linestyle='--')
axs[1].set_xlim(min(94,axs[1].get_xlim()[0]),max(106,axs[1].get_xlim()[1]))
axs[0].set_title(tr('(a) 超龄车辆步占比差'),loc='left',fontsize=10.6,color=navy,fontweight='bold',pad=8)
axs[1].set_title(tr('(b) 吞吐量之比'),loc='left',fontsize=10.6,color=navy,fontweight='bold',pad=8)
axs[0].set_xlabel(tr('双阶段减基线（百分点）'),color=navy,fontsize=8.7)
axs[1].set_xlabel(tr('双阶段 ÷ 基线（%）'),color=navy,fontsize=8.7)
fig.legend(handles=[Line2D([0],[0],color=blue,marker='o',markersize=4,label=tr('对拥堵规则')),
                    Line2D([0],[0],color=orange,marker='D',markersize=4,label=tr('对相对年龄规则'))],
           loc='lower center',bbox_to_anchor=(.58,-.002),ncol=2,
           frameon=False,fontsize=8.4)
export(fig,'fig7')


from validation import holdout_map

fig, axs = plt.subplots(1, 2, figsize=(7.35, 2.80))
fig.subplots_adjust(left=.05, right=.988, top=.88, bottom=.23, wspace=.12)
for j, (ax, name) in enumerate(zip(axs, ("ladder","offset"))):
    g = holdout_map(name)
    img = np.zeros((g.height,g.width))
    depots = set(g.depots[0]+g.depots[1])
    for k in g.cells:
        x,y = g.xy[k]
        img[y,x] = 2 if k in depots else 3 if g.bank(k)==0 else 1
    ax.imshow(img,cmap=ListedColormap(colors),vmin=0,vmax=3,origin='upper',interpolation='none')
    ax.set_xticks(np.arange(-.5,g.width,1),minor=True)
    ax.set_yticks(np.arange(-.5,g.height,1),minor=True)
    ax.grid(which='minor',color='#C5D0D8',lw=.34)
    ax.add_patch(Rectangle((8.5,-.5),3,13,fill=False,edgecolor=orange,lw=1,ls=(0,(4,2))))
    ax.set_xticks([0,4,9,11,16,20])
    ax.set_yticks([0,6,12] if j==0 else [])
    ax.tick_params(which='both',length=0,colors=grey,labelsize=8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title((tr('(a) 平行连通通道'),tr('(b) 错位连通通道'))[j],loc='left',color=navy,
                 fontsize=10.7,fontweight='bold',pad=6)
handles = [Patch(facecolor=fc,edgecolor=navy if idx==1 else fc,linewidth=.55,label=lab)
           for idx,(fc,lab) in enumerate(zip(colors,map(tr,('货架或隔墙','车道','可分配目标','瓶颈带内可通行格'))))]
fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.52,.015),
           ncol=4,frameon=False,fontsize=8.15,handlelength=1.3)
export(fig,'fig6')
