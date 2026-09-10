"""Render actual solved E12 tetrahedral fields, including real cut sections."""
from pathlib import Path
import json
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk,numpy_to_vtkIdTypeArray,vtk_to_numpy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.collections import PolyCollection
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
D=Path(__file__).resolve().parent
BG='#f7f7f3'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'figure.facecolor':BG,'axes.facecolor':BG})

def grid(name):
 r=json.loads((D/f'{name}-results.json').read_text());assert r['relative_free_residual']<1e-6
 d=np.load(D/f'{name}-solution.npz');g=vtk.vtkUnstructuredGrid();pts=vtk.vtkPoints();pts.SetData(numpy_to_vtk(d['p'],deep=True));g.SetPoints(pts)
 cells=vtk.vtkCellArray();cells.SetData(numpy_to_vtkIdTypeArray(np.arange(len(d['t'])+1,dtype=np.int64)*4,deep=True),numpy_to_vtkIdTypeArray(d['t'].astype(np.int64).ravel(),deep=True));g.SetCells(vtk.VTK_TETRA,cells)
 a=numpy_to_vtk(d['vm'],deep=True);a.SetName('vm');g.GetCellData().AddArray(a)
 return g,r

def poly_arrays(source):
 surface=vtk.vtkDataSetSurfaceFilter();surface.SetInputData(source);surface.Update()
 triangles=vtk.vtkTriangleFilter();triangles.SetInputConnection(surface.GetOutputPort());triangles.Update();p=triangles.GetOutput()
 pts=vtk_to_numpy(p.GetPoints().GetData());idx=vtk_to_numpy(p.GetPolys().GetConnectivityArray()).reshape(-1,3)
 values=vtk_to_numpy(p.GetCellData().GetArray('vm'))
 assert len(values)==len(idx)
 return pts[idx],values

def plane_slice(g,origin,normal):
 plane=vtk.vtkPlane();plane.SetOrigin(*origin);plane.SetNormal(*normal)
 c=vtk.vtkCutter();c.SetInputData(g);c.SetCutFunction(plane);c.GenerateTrianglesOn();c.Update()
 return poly_arrays(c.GetOutput())

def cutaway(g):
 plane=vtk.vtkPlane();plane.SetOrigin(0,0,12);plane.SetNormal(0,0,1)
 c=vtk.vtkClipDataSet();c.SetInputData(g);c.SetClipFunction(plane);c.Update()
 return c.GetOutput()

def surface3(ax,g,cap=6,landing=False):
 v,values=poly_arrays(g);xyz=v[:,:,[0,2,1]];norm=Normalize(0,cap);cmap=plt.get_cmap('turbo')
 collection=Poly3DCollection(xyz,facecolors=cmap(norm(values)),edgecolors='none',antialiased=False,rasterized=True)
 ax.add_collection3d(collection);lo=xyz.min((0,1));hi=xyz.max((0,1))
 ax.set(xlim=(lo[0],hi[0]),ylim=(0,24),zlim=(lo[2],hi[2]));dims=hi-lo;dims[1]=24
 ax.set_box_aspect(dims);ax.view_init(elev=22,azim=-55 if landing else -62)
 ax.set_xlabel('Projection X (mm)',labelpad=8);ax.set_ylabel('Width Z (mm)',labelpad=12);ax.set_zlabel('Height Y (mm)',labelpad=10);ax.set_yticks([0,12,24])
 return plt.cm.ScalarMappable(norm=norm,cmap=cmap)

def main():
 grids={n:grid(f'print-material-{n}w-h2') for n in [8,10]}
 for n,(g,r) in grids.items():
  fig=plt.figure(figsize=(13,9),layout='constrained');axes=[fig.add_subplot(1,2,i+1,projection='3d') for i in range(2)]
  artist=surface3(axes[0],g);surface3(axes[1],cutaway(g))
  axes[0].set_title('Complete printed-material domain');axes[1].set_title('Half-width cutaway / Z ≥ 12 mm')
  fig.colorbar(artist,ax=axes,shrink=.6,pad=.04,label='Element von Mises stress (MPa)',extend='max')
  fig.suptitle(f'E12 / solved 3D stress / {n} walls / 12 kg equivalent bracket load',fontsize=17,fontweight='bold')
  fig.supxlabel('Finished 50° chamfers, ideal contour walls and four continuous plates; sparse infill removed only for analysis.\nUndeformed geometry. Colour scale capped at 6 MPa; raw peaks and mesh sensitivity are reported separately.\nIsotropic numerical screening; no physical or lifetime qualification.',fontsize=10)
  fig.savefig(D/('fem-3d.png' if n==8 else 'fem-3d-10w.png'),dpi=155);plt.close(fig)
 fig,axes=plt.subplots(2,2,figsize=(12,11),layout='constrained',gridspec_kw={'height_ratios':[1.4,1]})
 for col,(n,(g,r)) in enumerate(grids.items()):
  for row,(origin,normal,coords) in enumerate([((0,0,8.2),(0,0,1),(0,1)),((90,0,0),(1,0,0),(2,1))]):
   v,values=plane_slice(g,origin,normal);ax=axes[row,col]
   # Same stress scale for both wall counts and cuts; no averaging/smoothing.
   pc=PolyCollection(v[:,:,coords],array=values,cmap='turbo',norm=Normalize(0,6),edgecolors='none',rasterized=True);ax.add_collection(pc)
   ax.autoscale();ax.set_aspect('equal')
   if row==0:
    ax.set(xlim=(-3,211),ylim=(-45,181),xlabel='Projection X (mm)',ylabel='Height Y (mm)',title=f'{n} walls / in-plane section\nInternal plate at Z = 8.2 mm')
    ax.axvline(90,color='#333333',lw=.7,ls='--')
   else:ax.set(xlim=(-1,25),ylim=(-44,-10),xlabel='Bracket width / print Z (mm)',ylabel='Height Y (mm)',title=f'{n} walls / transverse cut\nX = 90 mm')
 fig.colorbar(pc,ax=axes,shrink=.65,pad=.04,label='Element von Mises stress (MPa)',extend='max')
 fig.suptitle('E12 / sections through the solved 3D stress field',fontsize=17,fontweight='bold')
 fig.supxlabel('Actual intersections with solved tetrahedra; white internal regions receive zero sparse-infill credit.\nThe four plates connect through the perimeter walls. Colour scale capped at 6 MPa; peaks are not allowables.',fontsize=10)
 fig.savefig(D/'fem-sections.png',dpi=155);plt.close(fig)
 g,r=grid('landing-8w-h0.65');fig=plt.figure(figsize=(9,7),layout='constrained');ax=fig.add_subplot(111,projection='3d')
 artist=surface3(ax,g,landing=True);fig.colorbar(artist,ax=ax,shrink=.65,pad=.08,label='Element von Mises stress (MPa)')
 fig.suptitle('E12 / upper screw landing / 500 N washer compression',fontsize=16,fontweight='bold')
 fig.supxlabel('Actual 3.6 mm land and finished access geometry; flat rear support; nominal Ø13 / Ø5.5 washer patch.\nConstant-force submodel. Installed preload relaxation and a gap behind the land are not modeled.',fontsize=10)
 fig.savefig(D/'fem-landing.png',dpi=155);plt.close(fig)
 print('E12 full, cutaway, transverse/plate and landing stress views rendered',flush=True)

if __name__=='__main__':main()
