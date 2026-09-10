"""Compare the exact E12/E13 OpenSCAD side outlines before surface finishing."""
from pathlib import Path
import re,xml.etree.ElementTree as ET
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
D=Path(__file__).resolve().parent
def outline(rev):
 s=ET.parse(D.parent/f'closed-wall-{rev}'/'profile.svg').getroot().find('{http://www.w3.org/2000/svg}path').attrib['d']
 return np.array([[float(a),-float(b)] for a,b in re.findall(r'([-+\d.eE]+),([-+\d.eE]+)',s)])
p11=outline('e12');p12=outline('e13')
fig,(a,b)=plt.subplots(1,2,figsize=(12,7),layout='constrained',gridspec_kw={'width_ratios':[1,1.3]})
fig.set_facecolor('#f4f2eb')
for ax in [a,b]:
 ax.set_facecolor('#f4f2eb');ax.add_patch(Polygon(p11,fc='#d9d3c9',ec='#9b8472',lw=1,ls='--'))
 ax.add_patch(Polygon(p12,fc='#347b80',ec='#164c52',lw=1))
 ax.add_patch(Polygon(p11,fill=False,ec='#d8c7ad',lw=1.2,ls='--'))
 ax.set(aspect='equal',xlabel='Projection X (mm)',ylabel='Height Y (mm)');ax.spines[['top','right']].set_visible(False)
a.set(xlim=(-5,214),ylim=(-47,182),title='Complete side outline')
b.set(xlim=(28,152),ylim=(-47,23),title='Inner-seat detail / identical scale axes')
b.plot([48,134],[-32,-32],ls=':',color='#576a70',lw=1)
b.annotate('E13: +11 mm / straight flanks',xy=(91,-43),xytext=(42,-24),color='#f3f6ee',fontsize=12,arrowprops={'arrowstyle':'->','color':'#f3f6ee'})
b.text(63,16,'Dashed: E12 / +9.5 mm',color='#876c56',fontsize=11)
fig.suptitle('E13 / slightly deeper, straight-sided reinforcement',fontsize=18,fontweight='bold')
fig.supxlabel('Teal: E13 source outline · dashed grey: E12 · 1.5 mm more added depth · unchanged rod seats and fingers',fontsize=11)
fig.savefig(D/'depth-comparison.png',dpi=160)
