"""Draw actual helper layout changes clipped to the nominal body section."""
from pathlib import Path
import json,sys
import numpy as np
import shapely
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as PlotPath
from matplotlib.patches import PathPatch,Patch
from shapely.geometry.polygon import orient

D=Path(__file__).resolve().parent;ROOT=D.parents[1]
sys.path.insert(0,str(ROOT/'designs/rev-g'));import layout


def fill(ax,geometry,color,alpha=1.,edge='none',width=.3):
    parts=list(geometry.geoms) if hasattr(geometry,'geoms') else [geometry]
    for poly in parts:
        if poly.is_empty or poly.geom_type!='Polygon':continue
        poly=orient(poly,sign=1)
        paths=[]
        for ring in [poly.exterior,*poly.interiors]:
            vertices=np.asarray(ring.coords);codes=np.full(len(vertices),PlotPath.LINETO);codes[0]=PlotPath.MOVETO;codes[-1]=PlotPath.CLOSEPOLY
            paths.append(PlotPath(vertices,codes))
        ax.add_patch(PathPatch(PlotPath.make_compound_path(*paths),facecolor=color,edgecolor=edge,lw=width,alpha=alpha))


def main():
    output=D/'evolution-results/batch-02'
    summary=json.loads((output/'summary.json').read_text())
    base=json.loads((ROOT/'designs/rev-g/selected-layout.json').read_text())
    layers=json.loads((ROOT/'analysis/rev-f/inputs/e13-layer-outlines.json').read_text())
    z=12.1;body=shapely.from_wkb(bytes.fromhex(layers['wkb_hex'][60])).difference(layout.windows_at_z(base,z))
    original=layout.dense_at_z(layout.outline(),base,z).intersection(body)
    fig,axes=plt.subplots(2,3,figsize=(16,9),height_ratios=[3,1.2],layout='constrained')
    titles={'balanced':'A · Stiffness leader','stiffest':'B · Numerical check unresolved','economical':'C · Lighter seat helper'}
    for j,row in enumerate(summary['selected_for_actual_slice_3d']):
        p=row['parameters'];new=layout.dense_at_z(layout.outline(),p,z).intersection(body)
        added=new.difference(original);removed=original.difference(new)
        for i in [0,1]:
            ax=axes[i,j];fill(ax,body,'#e8ecef',edge='#64717b');fill(ax,original.intersection(new),'#c7a45c');fill(ax,added,'#009e88');fill(ax,removed,'#d25443')
            ax.set_aspect('equal');ax.set_xlim(-5,214);ax.set_ylim((-48,181) if i==0 else (-46,29));ax.axis('off')
        axes[0,j].set_title(titles[row['role']]+'\n'+row['id'],fontsize=12)
        changes=[f"{k.replace('_band','').replace('_',' ')}: {base[k]:g} → {p[k]:g} mm" for k in ['bottom_band','diagonal_band','seat_band','front_seat_band'] if p[k]!=base[k]]
        axes[1,j].text(.02,-.08,'\n'.join(changes),transform=axes[1,j].transAxes,fontsize=9,va='top')
    fig.legend(handles=[Patch(color='#e8ecef',label='Nominal body section'),Patch(color='#c7a45c',label='Existing dense helper'),Patch(color='#009e88',label='Added dense helper'),Patch(color='#d25443',label='Removed dense helper')],loc='outside lower center',ncol=4,frameon=False)
    fig.suptitle('G helper evolution · 100% infill allocation at mid-width\nSame exterior body; lower row enlarges the load-bearing arm. CAD section, not an actual toolpath or stress result.',fontsize=14)
    fig.savefig(output/'helper-directions.png',dpi=180,bbox_inches='tight');plt.close(fig)


if __name__=='__main__':main()
