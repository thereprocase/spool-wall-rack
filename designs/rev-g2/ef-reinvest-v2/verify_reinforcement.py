"""Verify the tapered helper connections after intersection with the real body."""
from pathlib import Path
import hashlib,json,sys,time
import cadquery as cq
D=Path(__file__).resolve().parent
sys.path.insert(0,str(D.parent/'ef-hybrid-v1'));import build_cad as shared
from reinforcement import tapered_regions

def installed(s):return s.translate((-250,-182,0)).rotate((0,0,0),(0,0,1),180)
def main():
    start=time.perf_counter();params=json.loads((D/'selected-layout.json').read_text())
    body=installed(cq.importers.importStep(str(D/'body-only.step')).val())
    background=installed(cq.importers.importStep(str(D/'dense-chords-and-seats.step')).val()).intersect(body)
    local=installed(cq.importers.importStep(str(D/'local-transition-backing.step')).val()).intersect(body)
    regions=tapered_regions(params);clipped=[shared.prism(r,0,24).intersect(body).clean() for r in regions]
    rows=[]
    for spec,part in zip(params['local_reinforcement'],clipped):
        overlap=part.intersect(background).Volume();assert part.isValid() and len(part.Solids())==1 and overlap>10
        rows.append(dict(name=spec['name'],valid=True,body_clipped_solid_count=1,body_clipped_volume_mm3=part.Volume(),overlap_with_existing_dense_body_mm3=overlap))
    joint=clipped[1].intersect(clipped[2]).Volume();assert joint>10
    joined=clipped[1].fuse(clipped[2]).clean();assert len(joined.Solids())==1 and joined.isValid()
    union=clipped[0].fuse(joined).clean()
    delta=union.cut(local).Volume()+local.cut(union).Volume();assert delta<1e-4
    r=dict(status='PASS_REAL_CAD_REINFORCEMENT_CONNECTIONS; SLICED_BONDS_CHECKED_SEPARATELY',regions=rows,post_to_lower_rail_overlap_mm3=joint,joined_rail_and_post_solid_count=1,delivered_local_helper_body_intersection_solid_count=len(local.Solids()),delivered_helper_symmetric_difference_mm3=delta,STEP_sha256={name:hashlib.sha256((D/name).read_bytes()).hexdigest() for name in ['body-only.step','dense-chords-and-seats.step','local-transition-backing.step']},elapsed_seconds=time.perf_counter()-start,scope='Checks clipped printable-body material, not connections through an external modifier halo. These are CAD overlap checks; actual credited deposited paths, layer bonds and load response require separate checks.')
    (D/'reinforcement-cad-verification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2),flush=True)
if __name__=='__main__':main()
