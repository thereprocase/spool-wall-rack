"""Compare the exact E11/E12 OpenSCAD side outlines before surface finishing."""
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
p11=outline('e11');p12=outline('e12')
fig,(a,b)=plt.subplots(1,2,figsize=(12,7),layout='constrained',gridspec_kw={'width_ratios':[1,1.3]})
fig.set_facecolor('#f4f2eb')
for ax in [a,b]:
 ax.set_facecolor('#f4f2eb');ax.add_patch(Polygon(p11,fc='#d9d3c9',ec='#9b8472',lw=1,ls='--'))
 ax.add_patch(Polygon(p12,fc='#347b80',ec='#164c52',lw=1))
 ax.set(aspect='equal',xlabel='Projection X (mm)',ylabel='Height Y (mm)');ax.spines[['top','right']].set_visible(False)
a.set(xlim=(-5,214),ylim=(-78,182),title='Complete side outline')
b.set(xlim=(47,135),ylim=(-76,23),title='Inner-seat detail / identical scale axes')
b.plot([48,134],[-32,-32],ls=':',color='#576a70',lw=1)
b.annotate('E12: +9.5 mm',xy=(90,-41.5),xytext=(60,-22),color='#f3f6ee',fontsize=12,arrowprops={'arrowstyle':'->','color':'#f3f6ee'})
b.annotate('E11: +38 mm',xy=(90,-70),xytext=(99,-58),color='#876c56',fontsize=12,arrowprops={'arrowstyle':'->','color':'#876c56'})
fig.suptitle('E12 / one-quarter of the previous protrusion',fontsize=18,fontweight='bold')
fig.supxlabel('Teal: E12 source outline · dashed grey: E11 · 75% less added depth · unchanged rod seats and fingers',fontsize=11)
fig.savefig(D/'depth-comparison.png',dpi=160)
