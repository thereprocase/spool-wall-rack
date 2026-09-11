"""Cut Rev G's windows from the actual finished E13 body; preserve its interfaces."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
import cadquery as cq
import layout
D=Path(__file__).resolve().parent;ROOT=D.parents[1]
SOURCE=ROOT/'designs/closed-wall-e13/body-only.step'

def wire(poly,z):
    points=np.array(poly.exterior.coords)[:-1]
    return cq.Wire.makePolygon([cq.Vector(x,y,z) for x,y in points],close=True)

def prism(poly,z,h):
    if poly.geom_type=='MultiPolygon':return cq.Compound.makeCompound([prism(p,z,h) for p in poly.geoms])
    outer=wire(poly,z)
    holes=[cq.Wire.makePolygon([cq.Vector(x,y,z) for x,y in list(ring.coords)[:-1]],close=True) for ring in poly.interiors]
    return cq.Solid.extrudeLinear(outer,holes,cq.Vector(0,0,h))

def outside_points(poly,d):
    p=np.array(poly.exterior.coords)[:-1]
    if not poly.exterior.is_ccw:p=p[::-1]
    edge=np.roll(p,-1,axis=0)-p;edge/=np.linalg.norm(edge,axis=1)[:,None]
    normal=np.column_stack([edge[:,1],-edge[:,0]])
    previous=np.roll(normal,1,axis=0)
    offset=(normal+previous)*d/(1+(normal*previous).sum(1))[:,None]
    return p,p+offset

def window_cutters(params):
    holes=layout.windows(params);polygons=list(holes.geoms) if holes.geom_type=='MultiPolygon' else [holes]
    cutters=[]
    for polygon in polygons:
        cutters.append(prism(polygon,-1,26))
        epsilon=.02;slope=np.tan(np.deg2rad(50))
        p,out=outside_points(polygon,layout.WINDOW_CHAMFER_INSET+epsilon/slope)
        a=cq.Wire.makePolygon([cq.Vector(x,y,-epsilon) for x,y in out],close=True)
        b=cq.Wire.makePolygon([cq.Vector(x,y,layout.WINDOW_CHAMFER_RISE) for x,y in p],close=True)
        bevel=cq.Solid.makeLoft([a,b],ruled=True)
        assert bevel.isValid()
        cutters.extend([bevel,bevel.mirror('XY').translate((0,0,24))])
    return cutters

def build(params,out=D):
    out.mkdir(parents=True,exist_ok=True)
    body=cq.importers.importStep(str(SOURCE)).val().translate((-250,-182,0)).rotate((0,0,0),(0,0,1),180)
    original=body
    for i,cutter in enumerate(window_cutters(params)):
        body=body.cut(cutter);assert body.isValid(),('window cut',i)
        print('window cutter',i+1,flush=True)
    body=body.clean()
    assert body.isValid() and len(body.Solids())==1
    assert body.cut(original).Volume()<1e-6
    a=original.BoundingBox();b=body.BoundingBox()
    for key in ['xmin','ymin','zmin','xmax','ymax','zmax']:assert abs(getattr(a,key)-getattr(b,key))<.001
    printed=body.rotate((0,0,0),(0,0,1),180).translate((250,182,0))
    cq.exporters.export(printed,str(out/'body-only.step'))
    cq.exporters.export(body.copy(),str(out/'body-mounted.stl'),tolerance=.02,angularTolerance=.08)
    cq.exporters.export(printed.copy(),str(out/'body-only.stl'),tolerance=.02,angularTolerance=.08)
    delivered=cq.importers.importStep(str(out/'body-only.step')).val()
    assert delivered.isValid() and len(delivered.Solids())==1
    record={'revision':'G','valid_body':True,'body_solid_count':1,
            'source_E13_STEP_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            'source_window_parameters':params,'original_CAD_volume_mm3':original.Volume(),
            'body_CAD_volume_mm3':delivered.Volume(),'new_window_chamfer_inset_mm':layout.WINDOW_CHAMFER_INSET,
            'new_window_chamfer_angle_deg':50,'body_print_bounds_mm':[getattr(printed.BoundingBox(),k) for k in ['xmin','ymin','zmin','xmax','ymax','zmax']],
            'note':'CAD envelope volume is not printed volume. Only the two specified angular windows and their mouth chamfers are removed.'}
    (out/'body-build-verification.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record),flush=True)
    return body

if __name__=='__main__':
    params=json.loads(Path(sys.argv[1]).read_text()) if len(sys.argv)>1 else {'window_scale':1.0}
    build(params,Path(sys.argv[2]) if len(sys.argv)>2 else D)
