"""Check intended reinforcement paths against raw credited deposited material."""
from pathlib import Path
import argparse,json,sys
import numpy as np
from shapely.geometry import LineString
from plastic_shape import PlasticShape

def pieces(g):
    if g.is_empty:return []
    if g.geom_type=='LineString':return [g]
    if hasattr(g,'geoms'):return [part for child in g.geoms for part in pieces(child)]
    return []

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--candidate',type=Path,required=True);ap.add_argument('--shape',type=Path,required=True);args=ap.parse_args()
    params=json.loads((args.candidate/'selected-layout.json').read_text());material=PlasticShape.load(args.shape)
    rows=[]
    for spec in params['local_reinforcement']:
        line=LineString(spec['points_XY_mm']);checked=[]
        for lo,hi,raw,_ in material.layers:
            z=(lo+hi)/2
            # G seat chamfers at broad faces are deliberately retained. Test
            # the full central width, where these designed centerlines lie.
            if not 2<=z<=22:continue
            missing=pieces(line.difference(raw));length=sum(v.length for v in missing);largest=max([v.length for v in missing],default=0)
            checked.append(dict(z_mid_mm=z,uncovered_length_mm=length,largest_uncovered_interval_mm=largest))
        maximum=max(v['largest_uncovered_interval_mm'] for v in checked)
        rows.append(dict(name=spec['name'],centerline_length_mm=line.length,layers_checked=len(checked),maximum_uncovered_interval_mm=maximum,centerline_covered_all_checked_layers=maximum<1e-6,layer_results=checked))
    connected=material.report['bond_connectivity']['connected_structural_components']==1
    r=dict(status='PASS_CREDITED_CENTERLINE_AND_COMPONENT_CHECKS' if connected and all(v['centerline_covered_all_checked_layers'] for v in rows) else 'REVIEW_UNCOVERED_CENTERLINE_INTERVALS',raw_credited_structural_components=material.report['bond_connectivity']['connected_structural_components'],paths=rows,shape_verification_sha256=__import__('hashlib').sha256((args.shape/'shape-verification.json').read_bytes()).hexdigest(),scope='Exact line coverage in every nominal raw structural slab between Z=2 and Z=22, plus full nominal layer-bond connectivity. Sacrificial bridges are excluded. This tests intended helper load paths; no pore closing, filled gaps or sacrificial bond credit is used. Physical bonding and the eroded solver geometry remain separate.')
    (args.candidate/'reinforcement-slice-connections.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k!='paths'},indent=2));print([(v['name'],v['maximum_uncovered_interval_mm']) for v in rows])
if __name__=='__main__':main()
