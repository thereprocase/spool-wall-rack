"""Gmsh tetrahedral meshes of analysis-only CAD; mm units."""
from pathlib import Path
import sys,gmsh,numpy as np
D=Path(__file__).resolve().parent
kind=sys.argv[1];n=int(sys.argv[2]);h=float(sys.argv[3]);name=f'{kind}-{n}w-h{h:g}'
gmsh.initialize();gmsh.option.setNumber('General.NumThreads',2)
gmsh.model.add(name);gmsh.model.occ.importShapes(str(D/f'{kind}-{n}w.brep'));gmsh.model.occ.synchronize()
gmsh.option.setNumber('Mesh.MeshSizeMin',.35 if kind=='landing' else .55)
gmsh.option.setNumber('Mesh.MeshSizeMax',h)
gmsh.option.setNumber('Mesh.MeshSizeFromPoints',0)
gmsh.option.setNumber('Mesh.MeshSizeFromCurvature',0)
gmsh.option.setNumber('Mesh.MeshSizeExtendFromBoundary',0)
gmsh.option.setNumber('Mesh.Algorithm3D',1)
gmsh.model.mesh.generate(3)
ids,p,_=gmsh.model.mesh.getNodes();p=np.array(p).reshape(-1,3)
types,tags,nodes=gmsh.model.mesh.getElements(3);cells=np.array(nodes[list(types).index(4)]).reshape(-1,4)
lookup=np.zeros(int(ids.max())+1,dtype=int);lookup[ids]=np.arange(len(ids));cells=lookup[cells]
used,inv=np.unique(cells,return_inverse=True);np.savez_compressed(D/f'{name}.npz',p=p[used],t=inv.reshape(-1,4))
print('SAVED',name,len(used),len(cells),flush=True);gmsh.finalize()
