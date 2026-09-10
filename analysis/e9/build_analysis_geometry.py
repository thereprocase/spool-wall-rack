"""Analysis-only printed-material surrogate; NEVER a print deliverable.
Preserves actual E9 outer body and functional cuts. Removes sparse core (zero credit),
leaves four 1.2 mm plates and idealized contour/tunnel perimeters.
"""
from pathlib import Path
import sys,json
import numpy as np
import cadquery as cq
from shapely.geometry import Polygon
from matplotlib.path import Path as MPath
D=Path(__file__).resolve().parent; SRC=D.parents[1]/'designs/closed-wall-e9'
sys.path.insert(0,str(SRC))
import build_step as b
from fastener_geometry import access_profile,x_prism,FIXINGS

def thickness(n):return .42+(n-1)*(.45-.2*(1-np.pi/4))
def build(n):
 p=b.read_polys('profile.svg')[0];b.boundary=MPath(p);poly=Polygon(p);t=thickness(n)
 body=cq.importers.importStep(str(SRC/'body-only.step')).val().translate((-250,-182,0)).rotate((0,0,0),(0,0,1),180)
 inner=poly.buffer(-t,quad_segs=8)
 if inner.geom_type!='Polygon':raise ValueError('Disconnected core')
 guard=[]
 for item in json.loads((SRC/'finish-specification.json').read_text())['edges']:
  a=np.array(item['a']);c=np.array(item['b']);fs=item['fade_start'];fe=item['fade_end']
  for top in [False,True]:guard.append(b.smooth_cutter(a,c,fs,fe,extra=t,top=top))
 keep=[x_prism(access_profile(y).buffer(t,quad_segs=8),0,220) for y in FIXINGS]
 for z,h in [(1.2,6.4),(8.8,6.4),(16.4,6.4)]:
  air=b.prism(np.array(inner.exterior.coords)[:-1],z,h)
  for g in guard+keep:air=air.cut(g)
  body=body.cut(air);print('walls',n,'core',z,flush=True)
 assert body.isValid() and len(body.Solids())==1
 cq.exporters.export(body,str(D/f'print-material-{n}w.brep'))
 # Actual landing coupon includes the land, 16 mm tunnel and surrounding print material.
 coupon=body.intersect(cq.Solid.makeBox(10,24,24,cq.Vector(0,152,0)))
 cq.exporters.export(coupon,str(D/f'landing-{n}w.brep'))
 return {'walls':n,'effective_wall_mm':t,'volume_mm3':body.Volume(),'valid':True}
if __name__=='__main__':
 results=[]
 for n in [8,10]:results.append(build(n))
 (D/'geometry.json').write_text(json.dumps(results,indent=2))
