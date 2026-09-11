"""Retain the EF body; remove one internal plate and thin the exterior skins."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import time
import cadquery as cq
from shapely.geometry import shape, box

D=Path(__file__).resolve().parent; SOURCE=D.parent/'ef-hybrid-v1'
sys.path.insert(0,str(SOURCE))
import build_cad as shared


def main():
    start=time.perf_counter();params=json.loads((D/'selected-layout.json').read_text())
    names=['body-only.step','body-only.stl','body-mounted.stl','geometry.geojson','projection-verification.json']
    for name in names: shutil.copyfile(SOURCE/name,D/name)
    original_receipt=json.loads((SOURCE/'cad-verification.json').read_text())
    body_print=cq.importers.importStep(str(D/'body-only.step')).val()
    body=body_print.translate((-250,-182,0)).rotate((0,0,0),(0,0,1),180)
    assert body.isValid() and len(body.Solids())==1
    outline=next(shape(v['geometry']) for v in json.loads((D/'geometry.geojson').read_text())['features']
                 if v['properties']['name']=='hybrid_body_projection')
    halo=outline.buffer(1.2,quad_segs=8).difference(outline.buffer(-.05,quad_segs=8))
    dense=shared.layout.dense_region(outline,params).union(halo).union(box(-16,65,.1,75))
    a,b=params['internal_plate_z_interval_mm']
    definitions=[('dense-chords-and-seats',dense,0,24),
                 ('central-rib-plane',outline.union(box(-16,105,1,115)),a,b-a)]
    assert [v[0] for v in definitions]==params['modifier_names']
    assembly=cq.Assembly(name='EF-LEAN-BODY-AND-MODIFIERS')
    assembly.add(body_print,name='BODY-print',color=cq.Color(.23,.52,.54));rows=[]
    for name,region,z,h in definitions:
        helper=shared.prism(region,z,h)
        if name=='dense-chords-and-seats':
            for _,profile,length in shared.layout.tunnel_saddles(params):
                saddle=shared.x_prism(profile,0,length).intersect(cq.Solid.makeBox(250,280,24,cq.Vector(-1,-80,0)))
                helper=helper.fuse(saddle)
        helper=helper.clean();assert helper.isValid()
        part=shared.printed(helper)
        cq.exporters.export(part,str(D/(name+'.step')))
        cq.exporters.export(part.copy(),str(D/(name+'.stl')),tolerance=.02,angularTolerance=.08)
        mesh=shared.repair_modifier(D/(name+'.stl'),len(helper.Solids()))
        roundtrip=cq.importers.importStep(str(D/(name+'.step'))).val()
        assert roundtrip.isValid() and abs(roundtrip.Volume()-helper.Volume())<1e-3
        assembly.add(part,name=name+'-MODIFIER-100pct',color=cq.Color(.88,.63,.22))
        rows.append(dict(name=name,valid=True,solid_count=len(helper.Solids()),z_min_mm=z,z_max_mm=z+h,
                         body_intersection_mm3=helper.intersect(body).Volume(),helper_volume_mm3=helper.Volume(),
                         role='100% infill modifier; never a printable part',STL_check=mesh))
        print('helper exported',name,flush=True)
    assembly.save(str(D/'bracket-with-modifiers.step'))
    delivered=cq.importers.importStep(str(D/'bracket-with-modifiers.step')).val()
    assert all(v.isValid() for v in delivered.Solids()) and len(delivered.Solids())==1+sum(r['solid_count'] for r in rows)
    hashes={name:hashlib.sha256((D/name).read_bytes()).hexdigest() for name in names}
    assert all(hashes[name]==hashlib.sha256((SOURCE/name).read_bytes()).hexdigest() for name in names)
    receipt=dict(status='PASS_CAD_AND_COPIED_BODY_PROVENANCE; PRINT_AND_MECHANICS_UNQUALIFIED',
                 body_valid=True,body_solids=1,body_source='ef-hybrid-v1',copied_files_sha256=hashes,
                 inherited_body_checks={k:original_receipt[k] for k in ['protected_interface_symmetric_difference_mm3',
                     'crown_moulding_keepout_overlap_mm3','fixed_rod_centers_XY_mm','fixing_checks','installed_bounds_mm']},
                 helpers=rows,assembly_solid_count=len(delivered.Solids()),skin_layers=4,
                 central_plate_z_interval_mm=[a,b],elapsed_seconds=time.perf_counter()-start,
                 scope='The outer EF body is retained byte for byte. Internal plate, skin and reinforcement parameters are recorded in selected-layout.json; actual saving and mechanics require a fresh slice and solve.')
    (D/'cad-verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2),flush=True)


if __name__=='__main__':main()
