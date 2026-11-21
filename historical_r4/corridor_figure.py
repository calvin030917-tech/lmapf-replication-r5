from collections import deque
from itertools import product
from matplotlib.patches import Rectangle, Circle, FancyArrowPatch
from matplotlib.lines import Line2D

def make_corridor_figure(plt, export, navy, blue, light, orange, sunset, grey, grid, tr):
    # State (A position, B position); each transition allows waiting and following,
    # but rules out shared destinations and opposite traversal of the same edge.
    main = ['a', 'b', 'c', 'd', 'e']
    def reachable(extra):
        edges = list(zip(main, main[1:])) + ([('c', 'r')] if extra else [])
        nodes = main + (['r'] if extra else [])
        moves = {a: [a] for a in nodes}
        for a, b in edges:
            moves[a].append(b)
            moves[b].append(a)
        q = deque([('b', 'd')])
        seen = set(q)
        while q:
            a, b = q.popleft()
            if (a, b) == ('e', 'a'):
                return True, moves
            for an, bn in product(moves[a], moves[b]):
                if an != bn and (an, bn) != (b, a) and (an, bn) not in seen:
                    q.append((an, bn))
                    seen.add((an, bn))
        return False, moves
    assert not reachable(False)[0]
    ok, moves = reachable(True)
    path_a = ['b', 'c', 'r', 'r', 'c', 'd', 'e']
    path_b = ['d', 'd', 'c', 'b', 'a', 'a', 'a']
    assert ok
    for (a,b),(an,bn) in zip(zip(path_a,path_b),list(zip(path_a,path_b))[1:]):
        assert an in moves[a] and bn in moves[b] and an != bn and (an,bn) != (b,a)

    fig,axs=plt.subplots(1,2,figsize=(7.35,3.15),gridspec_kw={'width_ratios':[1,1]})
    fig.subplots_adjust(left=.028,right=.977,top=.914,bottom=.113,wspace=.21)
    for j,ax in enumerate(axs):
        ax.set_xlim(-.5,5.1); ax.set_ylim(-1.93,1.95);ax.axis('off')
        ax.set_title([tr('(a) 无退避格'),tr('(b) 在中央增设退避格')][j],loc='left',color=navy,fontweight='bold',fontsize=11,pad=3)
        for i,x in enumerate(main):
            ax.add_patch(Rectangle((i,-.42),.95,.84,facecolor='#F7F9FA',edgecolor='#8797A5',lw=.85))
            ax.text(i+.475,-.56,x,ha='center',va='top',color=grey,fontsize=8.8)
        if j:
            ax.add_patch(Rectangle((2,.42),.95,.76,facecolor='#F3EACA',edgecolor='#8D6E39',lw=.85))
            ax.text(2.475,.79,'r',ha='center',va='center',color='#695026',fontsize=10.1,fontweight='bold')
            ax.text(2.475,1.42,tr('新增退避格'),ha='center',va='center',color='#695026',fontsize=8.4)
        for x,label,c in [(1,'A',blue),(3,'B',orange),(4,'A',blue),(0,'B',orange)]:
            start=x in (1,3)
            ax.add_patch(Circle((x+.475,0),.255,facecolor=c if start else 'white',edgecolor=c,lw=1.23,linestyle='-' if start else (0,(2,1))))
            ax.text(x+.475,0,label,ha='center',va='center',color='white' if start else c,fontsize=9.3,fontweight='bold')
        if not j:
            ax.text(.03,-1.02,tr('初始沿通道顺序：A 在 B 左侧'),color=navy,fontsize=9.1)
            ax.text(.03,-1.36,tr('目标要求两车交换左右顺序'),color=navy,fontsize=9.1)
            ax.text(.03,-1.71,tr('无法仅沿单列通道无冲突会车'),color=orange,fontsize=9.05,fontweight='bold')
        else:
            labels=[[tr('时刻')]+list('0123456'),[tr('车辆 A')]+path_a,[tr('车辆 B')]+path_b]
            widths=[.20]+[.80/7]*7
            tb=ax.table(cellText=labels,colWidths=widths,cellLoc='center',bbox=[.035,.018,.913,.246])
            tb.auto_set_font_size(False);tb.set_fontsize(7.9)
            for (ri,ci),cl in tb.get_celld().items():
                cl.set_edgecolor(grid);cl.set_linewidth(.55)
                if ri==0: cl.set_facecolor('#EAF0F4')
                elif ri==1 and labels[ri][ci]=='r': cl.set_facecolor('#F3EACA')
                else: cl.set_facecolor('white')
                cl.get_text().set_color([navy,blue,orange][ri])
    handles=[
        Line2D([],[],marker='o',color=navy,linestyle='None',label=tr('实心：起点'),markersize=5),
        Line2D([],[],marker='o',color=navy,markerfacecolor='white',linestyle='None',label=tr('空心：目标'),markersize=5),
        Rectangle((0,0),1,1,facecolor='#F3EACA',edgecolor='#8D6E39',lw=.8,label=tr('r：退避格')),
    ]
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.01),frameon=False,ncol=3,fontsize=8.5,handlelength=1.1,columnspacing=2.4)
    export(fig,'fig3')
