"""Extract full-width local fit coupons from current E10 finished CAD.
These retain the local exterior, seats and fingers; cut boundaries change
structural restraint, so they are fit checks, not load/creep qualification.
"""
from pathlib import Path
import cadquery as cq,json,sys
D=Path(__file__).resolve().parent
s=cq.importers.importStep(str(D.parent/'designs/closed-wall-e10/body-only.step')).val().translate((-250,-182,0)).rotate((0,0,0),(0,0,1),180)
sys.path.insert(0,str(D.parent/'designs/closed-wall-e10'))
from repair_stl import repair
rows=[]
for name,x0,x1,ymax in [('rear',65,115,22),('front',165,214,36)]:
 part=s.intersect(cq.Solid.makeBox(x1-x0,ymax+32,24,cq.Vector(x0,-32,0)))
 assert part.isValid() and len(part.Solids())==1
 part=part.translate((-x0,32,0));cq.exporters.export(part,str(D/f'{name}-fit-coupon.step'));cq.exporters.export(part,str(D/f'{name}-fit-coupon.stl'),tolerance=.02,angularTolerance=.08)
 mesh=repair(D/f'{name}-fit-coupon.stl')
 assembly=cq.Assembly(name=f'E10_{name.upper()}_FIT_COUPON')
 assembly.add(part,name='MAIN_BODY_SET_WALLS_AND_INFILL')
 bb=part.BoundingBox()
 for i,z in enumerate([7.6,15.2],1):
  helper=cq.Solid.makeBox(bb.xlen+4,bb.ylen+4,1.2,cq.Vector(bb.xmin-2,bb.ymin-2,z))
  assembly.add(helper,name=f'MODIFIER_{i}_100_PERCENT_INFILL')
 assembly.save(str(D/f'{name}-fit-coupon-with-helpers.step'))
 rows.append({'coupon':name,'valid_solid':True,'width_print_Z_mm':24,'source':'E10 finished body','mesh':mesh,'helper_bands_mm':[[7.6,8.8],[15.2,16.4]],'purpose':'Local fit only; cut boundaries do not reproduce whole-bracket restraint'})
(D/'coupon-verification.json').write_text(json.dumps(rows,indent=2))
