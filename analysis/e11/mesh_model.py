"""Gmsh tetrahedral meshes of analysis-only CAD; mm units."""
from pathlib import Path
import sys,json,gmsh,numpy as np
from mesh_quality import clean
D=Path(__file__).resolve().parent
kind=sys.argv[1];n=int(sys.argv[2]);h=float(sys.argv[3]);name=f'{kind}-{n}w-h{h:g}'
source=D/f'{kind}{"-clean" if "--clean" in sys.argv else ""}-{n}w.brep'
gmsh.initialize();gmsh.option.setNumber('General.NumThreads',2)
gmsh.model.add(name);gmsh.model.occ.importShapes(str(source));gmsh.model.occ.synchronize()
gmsh.option.setNumber('Mesh.MeshSizeMin',.35 if kind=='landing' else .55)
gmsh.option.setNumber('Mesh.MeshSizeMax',h)
gmsh.option.setNumber('Mesh.MeshSizeFromPoints',0)
gmsh.option.setNumber('Mesh.MeshSizeFromCurvature',0)
gmsh.option.setNumber('Mesh.MeshSizeExtendFromBoundary',0)
algorithm=int(sys.argv[4]) if len(sys.argv)>4 else 1
gmsh.option.setNumber('Mesh.Algorithm3D',algorithm)
try:gmsh.model.mesh.generate(3)
except Exception:
 # Retriangulate the same finite material with HXT if Delaunay cannot recover
 # a boundary. No CAD faces or finite-volume cells are discarded.
 gmsh.finalize();gmsh.initialize();gmsh.option.setNumber('General.NumThreads',2)
 gmsh.model.add(name);gmsh.model.occ.importShapes(str(source));gmsh.model.occ.synchronize()
 gmsh.option.setNumber('Mesh.MeshSizeMin',.35 if kind=='landing' else .55)
 gmsh.option.setNumber('Mesh.MeshSizeMax',h)
 gmsh.option.setNumber('Mesh.MeshSizeFromPoints',0)
 gmsh.option.setNumber('Mesh.MeshSizeFromCurvature',0)
 gmsh.option.setNumber('Mesh.MeshSizeExtendFromBoundary',0)
 algorithm=10
 gmsh.option.setNumber('Mesh.Algorithm3D',algorithm)
 gmsh.model.mesh.generate(3)
ids,p,_=gmsh.model.mesh.getNodes();p=np.array(p).reshape(-1,3)
types,tags,nodes=gmsh.model.mesh.getElements(3);cells=np.array(nodes[list(types).index(4)]).reshape(-1,4)
lookup=np.zeros(int(ids.max())+1,dtype=int);lookup[ids]=np.arange(len(ids));cells=lookup[cells]
p,cells,audit=clean(p,cells);used=np.arange(len(p));np.savez_compressed(D/f'{name}.npz',p=p,t=cells)
audit['gmsh_3d_algorithm']=algorithm
audit['source_BREP']=source.name
cad_volume=sum(gmsh.model.occ.getMass(3,tag) for dim,tag in gmsh.model.getEntities(3))
audit['CAD_volume_mm3']=cad_volume
audit['relative_mesh_CAD_volume_error']=abs(audit['total_absolute_volume_mm3']/cad_volume-1)
assert audit['relative_mesh_CAD_volume_error']<.005,audit
(D/f'{name}-mesh-quality.json').write_text(json.dumps(audit,indent=2))
print('SAVED',name,len(used),len(cells),flush=True);gmsh.finalize()
