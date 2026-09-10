"""Dimensioned modifier-stack diagram drawn from the STEP helper verification data."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
D=Path(__file__).resolve().parent
r=json.loads((D/'build-verification.json').read_text())
bg='#f3f1e9';ink='#235d65';gold='#cf993e';pale='#dce5e1'
fig,ax=plt.subplots(figsize=(12,7),facecolor=bg);ax.set_facecolor(bg)
ax.add_patch(Rectangle((0,0),5,24,fc=pale,ec=ink,lw=1.5))
for lo,hi in [(0,1.2),(22.8,24)]:ax.add_patch(Rectangle((0,lo),5,hi-lo,fc=ink))
for i,h in enumerate(r['helpers'],1):
 lo=h['z_min_mm'];hi=h['z_max_mm']
 ax.add_patch(Rectangle((-.4,lo),5.8,hi-lo,fc=gold,ec='#916628',lw=1))
 ax.annotate(f'HELPER {i} → 100% infill modifier\nZ = {lo:.1f}–{hi:.1f} mm · 1.2 mm thick',xy=(5.4,(lo+hi)/2),xytext=(7,(lo+hi)/2),va='center',fontsize=12,color=ink,arrowprops={'arrowstyle':'-','color':ink})
for lo,hi in [(1.2,7.6),(8.8,15.2),(16.4,22.8)]:
 ax.text(2.5,(lo+hi)/2,'Body infill\nuser-selected',ha='center',va='center',fontsize=11,color=ink)
ax.annotate('Top face: slicer top layers\n1.2 mm suggested',xy=(5,23.4),xytext=(7,23.4),va='center',fontsize=11,color=ink,arrowprops={'arrowstyle':'-','color':ink})
ax.annotate('Bottom face: slicer bottom layers\n1.2 mm suggested',xy=(5,.6),xytext=(7,.6),va='center',fontsize=11,color=ink,arrowprops={'arrowstyle':'-','color':ink})
ax.plot([-.7,5.7],[-.15,-.15],lw=3,color='#657d82');ax.text(2.5,-1.6,'BUILD PLATE',ha='center',fontsize=10,color=ink)
ax.set_xlim(-1.8,18);ax.set_ylim(-2,26);ax.set_yticks(range(0,25,4));ax.set_ylabel('Print height Z / mm',color=ink);ax.set_xticks([])
ax.spines[['top','right','bottom']].set_visible(False)
fig.suptitle('E9 / LET THE SLICER GENERATE THE INFILL',x=.07,y=.95,ha='left',fontsize=20,fontweight='bold',color=ink)
fig.text(.07,.87,'STEP assembly: one solid body + two overlapping helper solids',fontsize=13,color=ink)
fig.text(.07,.035,'Stack schematic, not sliced paths. Keep parts aligned; convert helpers to modifiers before slicing.',fontsize=10,color=ink)
fig.subplots_adjust(top=.81,bottom=.12,left=.08,right=.98)
fig.savefig(D/'modifier-stack.png',dpi=160,facecolor=bg)
