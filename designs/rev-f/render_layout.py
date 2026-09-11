"""Exact planar helper masks and voids, in installed coordinates."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch
from shapely.geometry import box
import layout
D=Path(__file__).resolve().parent

def draw(ax,shape,color,**kwargs):
    polygons=list(shape.geoms) if shape.geom_type=='MultiPolygon' else [shape]
    for polygon in polygons:
        if polygon.is_empty:continue
        polygon=__import__('shapely').geometry.polygon.orient(polygon,sign=1)
        vertices=[];codes=[]
        for ring in [polygon.exterior,*polygon.interiors]:
            pts=list(ring.coords);vertices+=pts;codes += [MPath.MOVETO]+[MPath.LINETO]*(len(pts)-2)+[MPath.CLOSEPOLY]
        ax.add_patch(PathPatch(MPath(vertices,codes),facecolor=color,**kwargs))

def main():
    params=json.loads((D/'selected-layout.json').read_text());outline=layout.outline();body=outline.difference(layout.windows(params))
    dense=layout.dense_region(outline,params).intersection(body);ribs=layout.rib_plane_region(outline,params).intersection(body)
    fig,axes=plt.subplots(1,3,figsize=(15,6.2),layout='constrained',facecolor='#f3f1e9')
    titles=['1 / Dense chords and seats','2 / Lower rib plane','3 / Upper rib plane']
    subtitles=['Z = 0–24 mm','Z = 7.6–8.8 mm','Z = 15.2–16.4 mm']
    for i,(ax,mask,y) in enumerate(zip(axes,[dense,ribs,ribs],[70,110,130])):
        ax.set_facecolor('#f3f1e9');draw(ax,body,'#d9e4e2',edgecolor='#31545b',linewidth=.7)
        draw(ax,mask,'#c89032',edgecolor='none')
        draw(ax,box(-16,y-5,0,y+5),'#c89032',edgecolor='#31545b',linewidth=.6)
        ax.annotate('selection tab\n(outside body)',xy=(-10,y),xytext=(30,y+23),fontsize=8,color='#344e53',arrowprops={'arrowstyle':'-','color':'#677d7e'})
        ax.set(xlim=(-21,215),ylim=(-48,183),aspect='equal',title=titles[i]+'\n'+subtitles[i],xlabel='Projection from wall (mm)')
        ax.spines[['top','right']].set_visible(False)
    axes[0].set_ylabel('Installed height (mm)')
    fig.suptitle('REV F / precise modifier footprints',fontsize=19,fontweight='bold',color='#243d43')
    fig.supxlabel('Gold: 100% infill regions clipped to the body · pale teal: body envelope, with slicer-controlled walls and sparse core.\nTwo angular windows remain empty. External connector halo omitted for clarity; tabs and halo must not print.',fontsize=10,color='#344e53')
    fig.savefig(D/'modifier-layout.png',dpi=170);plt.close(fig)
    print('Modifier layout rendered',flush=True)

if __name__=='__main__':main()
