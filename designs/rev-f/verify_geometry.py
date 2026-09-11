"""Independent delivered-STEP interface preservation and new window finish audit."""
from pathlib import Path
import json,hashlib,math
import cadquery as cq
from shapely.geometry import Point
import layout
D=Path(__file__).resolve().parent

def read(path):return cq.importers.importStep(str(path)).val().translate((-250,-182,0)).rotate((0,0,0),(0,0,1),180)

def main():
    source=D.parent/'closed-wall-e13/body-only.step';baseline=read(source);body=read(D/'body-only.step')
    assert body.isValid() and len(body.Solids())==1
    assert body.cut(baseline).Volume()<1e-6
    checks=[]
    guards=[('back wall and screw lands',cq.Solid.makeBox(8,230,26,cq.Vector(-1,-46,-1))),
            ('inner seat, fingers and rigid shoulders',cq.Solid.makeCylinder(22,26,cq.Vector(90,0,-1))),
            ('outer seat, fingers and rigid shoulders',cq.Solid.makeCylinder(22,26,cq.Vector(190,12,-1))),
            ('upper fixing and tool access',cq.Solid.makeBox(35,30,26,cq.Vector(-1,149,-1))),
            ('lower fixing and tool access',cq.Solid.makeBox(35,30,26,cq.Vector(-1,25,-1)))]
    for name,mask in guards:
        old=baseline.intersect(mask);new=body.intersect(mask)
        missing=old.cut(new).Volume();added=new.cut(old).Volume()
        assert missing<1e-5 and added<1e-5,(name,missing,added)
        checks.append({'interface':name,'missing_volume_mm3':missing,'added_volume_mm3':added,'unchanged':True})
    params=json.loads((D/'selected-layout.json').read_text());windows=layout.windows(params)
    chamfers=[]
    for face in body.Faces():
        c=face.Center()
        if not(1e-5<c.z<layout.WINDOW_CHAMFER_RISE or 24-layout.WINDOW_CHAMFER_RISE<c.z<24-1e-5):continue
        if windows.boundary.distance(Point(c.x,c.y))>1:continue
        # Ruled planar loft facets may be stored by OCC as BSPLINE surfaces.
        # Measure their actual normals rather than accepting only a type label.
        n=face.normalAt();angle=math.degrees(math.acos(min(1,abs(n.z))))
        if 1<angle<89:
            assert abs(angle-50)<1e-5,(c.toTuple(),angle)
            chamfers.append({'center_mm':list(c.toTuple()),'surface_type':face.geomType(),'angle_above_bed_deg':angle})
    assert len(chamfers)>20
    a=baseline.BoundingBox();b=body.BoundingBox()
    for k in ['xmin','ymin','zmin','xmax','ymax','zmax']:assert abs(getattr(a,k)-getattr(b,k))<.001
    record={'body_valid':True,'body_solids':1,'E13_STEP_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'Rev_F_STEP_sha256':hashlib.sha256((D/'body-only.step').read_bytes()).hexdigest(),
            'added_outside_E13_mm3':0.,'preserved_interfaces':checks,'same_external_bounds':True,
            'window_chamfer_facets':chamfers,'window_chamfer_min_deg':min(x['angle_above_bed_deg'] for x in chamfers),
            'window_chamfer_max_deg':max(x['angle_above_bed_deg'] for x in chamfers),
            'scope':'Independent Boolean comparisons of delivered STEP files. E13 rod clearance and hardware geometry remain; physical fit, insertion force and long-term behavior are untested.'}
    (D/'geometry-verification.json').write_text(json.dumps(record,indent=2)+'\n')
    print('STEP interface and window chamfer checks passed',flush=True)

if __name__=='__main__':main()
