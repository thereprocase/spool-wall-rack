"""Exact planar helper masks and voids, in installed coordinates."""
from pathlib import Path
import json,importlib.util,sys
import vtk
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch
from shapely.geometry import box
import layout
D=Path(__file__).resolve().parent


def section(name,z):
    """Cut the delivered mesh and return the exact nominal interior at Z."""
    sys.path.insert(0,str(D.parent/'closed-wall-e13'))
    spec=importlib.util.spec_from_file_location('e13_paths',D.parent/'closed-wall-e13/inspect_toolpaths.py')
    base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
    reader=vtk.vtkSTLReader();reader.SetFileName(str(D/name));reader.Update()
    tr=vtk.vtkTransform();tr.Translate(250,182,0);tr.RotateZ(180)
    tf=vtk.vtkTransformPolyDataFilter();tf.SetInputData(reader.GetOutput());tf.SetTransform(tr);tf.Update()
    mesh=tf.GetOutput();inside=vtk.vtkSelectEnclosedPoints();inside.Initialize(mesh)
    return base.layer_polygons(mesh,z,inside)

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
    params=json.loads((D/'selected-layout.json').read_text());bands=layout.plate_bands(params)
    levels=[12.,sum(bands[1])/2,sum(bands[2])/2]
    names=['dense-chords-and-seats','rib-plane-lower','rib-plane-upper']
    fig,axes=plt.subplots(1,3,figsize=(15,6.2),layout='constrained',facecolor='#f3f1e9')
    titles=['1 / Chords, seats and fixing support','2 / Lower full plane','3 / Upper full plane']
    subtitles=[f'Section at Z = {levels[0]:g} mm',f'Band Z = {bands[1][0]:g}–{bands[1][1]:g} mm',f'Band Z = {bands[2][0]:g}–{bands[2][1]:g} mm']
    for i,(ax,z,name,y) in enumerate(zip(axes,levels,names,[70,110,130])):
        body=section('body-only.stl',z);mask=section(name+'.stl',z).intersection(body)
        ax.set_facecolor('#f3f1e9');draw(ax,body,'#d9e4e2',edgecolor='#31545b',linewidth=.7)
        draw(ax,mask,'#c89032',edgecolor='none')
        draw(ax,box(-16,y-5,0,y+5),'#c89032',edgecolor='#31545b',linewidth=.6)
        ax.annotate('selection tab\n(outside body)',xy=(-10,y),xytext=(30,y+23),fontsize=8,color='#344e53',arrowprops={'arrowstyle':'-','color':'#677d7e'})
        ax.set(xlim=(-21,215),ylim=(-48,183),aspect='equal',title=titles[i]+'\n'+subtitles[i],xlabel='Projection from wall (mm)')
        ax.spines[['top','right']].set_visible(False)
    axes[0].set_ylabel('Installed height (mm)')
    fig.suptitle('REV G / sections through the delivered modifiers',fontsize=19,fontweight='bold',color='#243d43')
    fig.supxlabel('Gold: actual modifier mesh clipped to actual body mesh · pale teal: body envelope.\nFixing support varies through Z; its center section is shown. Air-only halo omitted; selection tabs are shown separately and must not print.',fontsize=10,color='#344e53')
    fig.savefig(D/'modifier-layout.png',dpi=170);plt.close(fig)
    print('Modifier layout rendered',flush=True)

if __name__=='__main__':main()
