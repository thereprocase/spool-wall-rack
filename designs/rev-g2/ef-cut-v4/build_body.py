"""Remove upper-mast width from the lean EF body without changing interfaces."""
from pathlib import Path
import hashlib,json,shutil,sys,time
import cadquery as cq
from shapely.geometry import Polygon
D=Path(__file__).resolve().parent;SOURCE=D.parent/'ef-cut-v3';REFERENCE=D.parent/'ef-hybrid-v1'
sys.path.insert(0,str(REFERENCE));import build_cad as shared

def main():
    start=time.perf_counter();p=json.loads((D/'selected-layout.json').read_text());q=p['mast_relief']
    before_print=cq.importers.importStep(str(SOURCE/'body-only.step')).val()
    before=before_print.translate((-250,-182,0)).rotate((0,0,0),(0,0,1),180)
    profile=Polygon([(q['Y_start_mm'],24),(q['Y_lower_flat_mm'],q['remaining_Z_thickness_mm']),
                     (q['Y_upper_flat_mm'],q['remaining_Z_thickness_mm']),(q['Y_end_mm'],24),
                     (q['Y_end_mm'],30),(q['Y_start_mm'],30)])
    tool=shared.x_prism(profile,-1,18)
    body=before.cut(tool).clean();removed=before.cut(body)
    assert body.isValid() and len(body.Solids())==1 and body.cut(before).Volume()<1e-7
    guard=cq.Solid.makeBox(240,120,30,cq.Vector(-1,-58,-1)).fuse(cq.Solid.makeBox(60,30,30,cq.Vector(-1,150,-1)))
    protected=removed.intersect(guard).Volume();assert protected<1e-7
    # Every original low-Z section is retained, providing a flat connected
    # print base. The top relief grows as layers rise; it creates no roof.
    bottom=removed.intersect(cq.Solid.makeBox(240,280,6,cq.Vector(-1,-60,0))).Volume();assert bottom<1e-7
    body_print=shared.printed(body)
    cq.exporters.export(body_print,str(D/'body-only.step'))
    cq.exporters.export(body_print.copy(),str(D/'body-only.stl'),tolerance=.02,angularTolerance=.08)
    mesh=shared.repair_modifier(D/'body-only.stl',1)
    cq.exporters.export(body.copy(),str(D/'body-mounted.stl'),tolerance=.02,angularTolerance=.08)
    mounted=shared.repair_modifier(D/'body-mounted.stl',1)
    rt=cq.importers.importStep(str(D/'body-only.step')).val();assert rt.isValid() and len(rt.Solids())==1 and abs(rt.Volume()-body.Volume())<1e-3
    assembly=cq.Assembly(name='EF-MAST-CUT-AND-MODIFIERS');assembly.add(body_print,name='BODY-print')
    rows=[]
    for name in p['modifier_names']:
        for ext in ['.step','.stl']:shutil.copyfile(SOURCE/(name+ext),D/(name+ext))
        helper_print=cq.importers.importStep(str(D/(name+'.step'))).val();helper=helper_print.translate((-250,-182,0)).rotate((0,0,0),(0,0,1),180)
        assert helper.isValid();assembly.add(helper_print,name=name+'-MODIFIER-100pct')
        rows.append(dict(name=name,solid_count=len(helper.Solids()),body_intersection_mm3=helper.intersect(body).Volume(),role='100% infill modifier; never a printable part',copied_STEP_sha256=hashlib.sha256((D/(name+'.step')).read_bytes()).hexdigest()))
    for name in ['geometry.geojson','projection-verification.json']:shutil.copyfile(SOURCE/name,D/name)
    assembly.save(str(D/'bracket-with-modifiers.step'));rt=cq.importers.importStep(str(D/'bracket-with-modifiers.step')).val()
    assert len(rt.Solids())==1+sum(v['solid_count'] for v in rows) and all(v.isValid() for v in rt.Solids())
    original=json.loads((REFERENCE/'cad-verification.json').read_text())
    r={k:original[k] for k in ['protected_interface_symmetric_difference_mm3','crown_moulding_keepout_overlap_mm3','fixed_rod_centers_XY_mm','fixing_checks','installed_bounds_mm']}
    r.update(status='PASS_SUBTRACTIVE_BODY_AND_RETAINED_INTERFACE_CHECKS; PHYSICAL_AND_MECHANICAL_QUALIFICATION_OPEN',body_valid=True,body_solids=1,body_source='ef-cut-v3',body_CAD_envelope_volume_mm3=body.Volume(),removed_upper_mast_CAD_volume_mm3=removed.Volume(),new_removed_material_inside_protected_guard_mm3=protected,removed_material_below_Z6_mm3=bottom,body_STL_check=mesh,mounted_STL_check=mounted,helpers=rows,assembly_solid_count=len(rt.Solids()),elapsed_seconds=time.perf_counter()-start,scope='Only upper mast through-width material is removed. XY projection, moulding, rods and hardware are retained. CAD removed volume is not saved filament. The 6 mm web lies on the print base; its sloped top has no unsupported roof. Current-load low energy is an allocation clue, not qualification for other loads.')
    (D/'cad-verification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2),flush=True)
if __name__=='__main__':main()
