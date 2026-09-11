"""Check local reinforcement load routes through raw credited layer bonds."""
from pathlib import Path
import argparse,importlib.util,json,hashlib
import numpy as np
import shapely
from shapely.geometry import Point,LineString
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from plastic_shape import PlasticShape,polygons

def local_route(material,region,spec):
    layers=[(a,b,raw.intersection(region)) for a,b,raw,_ in material.layers]
    parts=[polygons(g) for _,_,g in layers];offsets=np.r_[0,np.cumsum([len(p) for p in parts])];links=[]
    for k in range(1,len(layers)):
        if abs(layers[k-1][1]-layers[k][0])>1e-7 or not parts[k-1] or not parts[k]:continue
        tree=shapely.STRtree(parts[k-1])
        for i,poly in enumerate(parts[k]):
            for j in tree.query(poly,predicate='intersects'):
                if poly.intersection(parts[k-1][j]).area>1e-8:links.append((offsets[k]+i,offsets[k-1]+j))
    links=np.asarray(links,dtype=int).reshape(-1,2);n=offsets[-1]
    graph=coo_matrix((np.ones(len(links)),(links[:,0],links[:,1])),shape=(n,n));count,labels=connected_components(graph,directed=False)
    volumes=np.zeros(count);anchor_volumes=np.zeros((2,count))
    anchors=[Point(spec['points_XY_mm'][i]).buffer(min(1.,spec['radii_mm'][i]/2),quad_segs=16) for i in [0,-1]]
    for k,(lo,hi,_) in enumerate(layers):
        for j,poly in enumerate(parts[k]):
            component=labels[offsets[k]+j];volumes[component]+=poly.area*(hi-lo)
            for side,anchor in enumerate(anchors):anchor_volumes[side,component]+=poly.intersection(anchor).area*(hi-lo)
    main=int(volumes.argmax());ratios=anchor_volumes[:,main]/anchor_volumes.sum(axis=1)
    assert np.isfinite(ratios).all()
    return dict(name=spec['name'],regional_material_components=int(count),all_component_volumes_mm3=sorted(volumes.tolist(),reverse=True),main_component_fraction=float(volumes[main]/volumes.sum()),anchor_volume_fraction_in_main_component=ratios.tolist(),main_component_connects_both_anchors=bool(np.all(ratios>.99)),raw_region_volume_mm3=float(volumes.sum()),layer_bond_links=len(links),minimum_bond_overlap_area_mm2=1e-8)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--candidate',type=Path,required=True);ap.add_argument('--shape',type=Path,required=True);args=ap.parse_args()
    p=json.loads((args.candidate/'selected-layout.json').read_text());material=PlasticShape.load(args.shape)
    spec=importlib.util.spec_from_file_location('reinforcement',args.candidate/'reinforcement.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    rows=[local_route(material,r,s) for r,s in zip(module.tapered_regions(p),p['local_reinforcement'])]
    if p.get('direct_brace_core'):
        b=p['direct_brace'];spec=dict(name='direct-brace-core',points_XY_mm=b['points_XY_mm'],radii_mm=[b['radius_mm']]*len(b['points_XY_mm']))
        rows.append(local_route(material,LineString(b['points_XY_mm']).buffer(b['radius_mm'],quad_segs=16),spec))
    passes=all(r['main_component_connects_both_anchors'] and r['main_component_fraction']>.99 for r in rows)
    report=dict(status='PASS_LOCAL_CREDITED_BOND_ROUTES' if passes else 'REVIEW_LOCAL_BOND_ROUTE',regions=rows,all_raw_material_components=material.report['bond_connectivity']['connected_structural_components'],shape_verification_sha256=hashlib.sha256((args.shape/'shape-verification.json').read_bytes()).hexdigest(),scope='Positive-area bonds between touching raw structural layers, restricted separately to each designed helper footprint. At least 99 percent of each endpoint anchor and local credited volume must lie in the same connected route. All regional components are retained and reported. No filled pores, closing, remote routes through the rest of the bracket, or sacrificial bridge bonds are used. Straight centerline coverage is a separate stricter diagnostic and can encounter pores even when this material route remains connected. Physical bond strength and the inscribed numerical mesh remain separate.')
    (args.candidate/'reinforcement-bond-connections.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
