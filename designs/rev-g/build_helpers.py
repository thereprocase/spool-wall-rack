"""Separate named 100% infill helpers, with selection tabs outside the body."""
from pathlib import Path
import json,hashlib,sys
import cadquery as cq
from shapely.geometry import box
import layout
from build_body import prism
from repair_stl import repair
D=Path(__file__).resolve().parent
if len(sys.argv)>1:D=Path(sys.argv[1]).resolve()

def printed(shape):
    return shape.rotate((0,0,0),(0,0,1),180).translate((250,182,0))

def helper_regions(params):
    outline=layout.outline()
    # Air-only halo connects the dense islands into a single selectable part.
    # The 0.05 mm inward overlap lies inside every candidate's outer wall.
    halo=outline.buffer(1.2,quad_segs=8).difference(outline.buffer(-.05,quad_segs=8))
    dense=layout.dense_region(outline,params).union(halo).union(box(-16,65,.1,75))
    ribs=layout.rib_plane_region(outline,params)
    bands=layout.plate_bands(params)
    return [('dense-chords-and-seats',dense,0.,24.),
            ('rib-plane-lower',ribs.union(box(-16,105,1,115)),bands[1][0],bands[1][1]-bands[1][0]),
            ('rib-plane-upper',ribs.union(box(-16,125,1,135)),bands[2][0],bands[2][1]-bands[2][0])]

def main():
    params=json.loads((D/'selected-layout.json').read_text())
    body=cq.importers.importStep(str(D/'body-only.step')).val()
    mounted=body.translate((-250,-182,0)).rotate((0,0,0),(0,0,1),180)
    assembly=cq.Assembly(name='Rev-G-body-and-modifiers')
    assembly.add(body,name='BODY-print',color=cq.Color(.23,.52,.54))
    rows=[];meshes=[]
    for name,region,z,h in helper_regions(params):
        helper=prism(region,z,h).clean()
        if name=='dense-chords-and-seats':
            for label,profile,length in layout.tunnel_saddles(params):
                wire=cq.Wire.makePolygon([cq.Vector(0,y,zz) for y,zz in list(profile.exterior.coords)[:-1]],close=True)
                saddle=cq.Solid.extrudeLinear(wire,[],cq.Vector(length,0,0))
                # Keep the saddle solid across air, capped to the printed width.
                # Orca clips it to the body. Avoid carving closed internal void
                # shells into selection geometry; the printable intersection
                # is unchanged by the distributive law of these unions.
                helper=helper.fuse(saddle.intersect(cq.Solid.makeBox(220,240,24,cq.Vector(-1,-50,0)))).clean()
        assert helper.isValid() and len(helper.Solids())==1,(name,len(helper.Solids()))
        actual=helper.intersect(mounted)
        tab=prism(box(-16,z*0+65,-1,75),z,h) if name.startswith('dense') else prism(box(-16,105 if z<10 else 125,-1,115 if z<10 else 135),z,h)
        assert tab.intersect(mounted).Volume()<1e-8
        part=printed(helper)
        cq.exporters.export(part,str(D/f'{name}.step'))
        cq.exporters.export(part.copy(),str(D/f'{name}.stl'),tolerance=.02,angularTolerance=.08)
        meshes.append(repair(D/f'{name}.stl'))
        assembly.add(part,name=name+'-MODIFIER-100pct',color=cq.Color(.88,.63,.22))
        rows.append({'name':name,'z_min_mm':z,'z_max_mm':z+h,'valid':True,'solid_count':1,
                     'helper_volume_mm3':helper.Volume(),'body_intersection_mm3':actual.Volume(),
                     'tab_body_intersection_mm3':0.,'role':'100% infill modifier; never a printable part'})
        print('helper complete',name,flush=True)
    assembly.save(str(D/'bracket-with-modifiers.step'))
    delivered=cq.importers.importStep(str(D/'bracket-with-modifiers.step')).val()
    assert len(delivered.Solids())==4 and all(s.isValid() for s in delivered.Solids())
    (D/'helper-verification.json').write_text(json.dumps({'layout_sha256':layout.layout_hash(params),
        'parts':rows,'delivered_STEP_solids':4,'STL_checks':meshes,
        'note':'STEP encodes geometry and names, not slicer behavior. The model-only 3MF supplies modifier roles.'},indent=2)+'\n')

if __name__=='__main__':main()
