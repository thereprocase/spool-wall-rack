"""Spend the saved material on a continuous full-density direct brace core."""
from pathlib import Path
import json,sys,time
import cadquery as cq
from shapely.geometry import LineString
D=Path(__file__).resolve().parent;ROOT=D.parents[3]
sys.path.insert(0,str(ROOT/'designs/rev-g2/ef-hybrid-v1'));import build_cad as shared

def installed(p):return p.translate((-250,-182,0)).rotate((0,0,0),(0,0,1),180)
def main():
    start=time.perf_counter();p=json.loads((D/'selected-layout.json').read_text());q=p['direct_brace']
    body_print=cq.importers.importStep(str(D/'body-only.step')).val();body=installed(body_print)
    core=shared.prism(LineString(q['points_XY_mm']).buffer(q['radius_mm'],quad_segs=16),0,24)
    core_print=shared.printed(core);cq.exporters.export(core_print,str(D/'direct-brace-core.step'));cq.exporters.export(core_print.copy(),str(D/'direct-brace-core.stl'),tolerance=.02,angularTolerance=.08)
    mesh=shared.repair_modifier(D/'direct-brace-core.stl',1)
    clipped=core.intersect(body).clean();assert clipped.isValid() and len(clipped.Solids())==1
    background=installed(cq.importers.importStep(str(D/'dense-chords-and-seats.step')).val()).intersect(body)
    local=installed(cq.importers.importStep(str(D/'local-transition-backing.step')).val()).intersect(body)
    dense_overlap=clipped.intersect(background).Volume();local_overlap=clipped.intersect(local).Volume();assert min(dense_overlap,local_overlap)>100
    assembly=cq.Assembly(name='EF-SOLID-BRACE-CORE-AND-MODIFIERS');assembly.add(body_print,name='BODY-print');count=1
    for name in p['modifier_names']:
        part=cq.importers.importStep(str(D/(name+'.step'))).val();assert part.isValid();assembly.add(part,name=name+'-MODIFIER-100pct');count+=len(part.Solids())
    assembly.save(str(D/'bracket-with-modifiers.step'));rt=cq.importers.importStep(str(D/'bracket-with-modifiers.step')).val();assert len(rt.Solids())==count and all(v.isValid() for v in rt.Solids())
    r=dict(status='PASS_CONTINUOUS_CORE_CAD_AND_REAL_BODY_JUNCTIONS',body_clipped_core_solids=1,body_clipped_core_volume_mm3=clipped.Volume(),core_overlap_with_existing_dense_material_mm3=dense_overlap,core_overlap_with_bearing_to_keel_helper_mm3=local_overlap,assembly_solid_count=count,STL_check=mesh,elapsed_seconds=time.perf_counter()-start,scope='Body geometry is unchanged. The core is a 100 percent infill modifier, not additional geometry. Both overlaps are inside the real body. Actual extrusion, credited layer bonds and mechanics are checked separately.')
    (D/'core-verification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2),flush=True)
if __name__=='__main__':main()
