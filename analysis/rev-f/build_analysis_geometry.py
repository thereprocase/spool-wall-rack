"""Rev F ideal perimeter/skin/rib domain from finished CAD; no sparse infill credit."""
from pathlib import Path
import importlib.util,sys,json,hashlib
import cadquery as cq
from shapely import union_all
D=Path(__file__).resolve().parent;ROOT=D.parents[1];SRC=ROOT/'designs/rev-f'
sys.path.insert(0,str(SRC))
import layout
from build_body import prism

def main():
    params=json.loads((Path(sys.argv[1]) if len(sys.argv)>1 else SRC/'selected-layout.json').read_text());n=params['walls']
    out=Path(sys.argv[2]) if len(sys.argv)>2 else D
    out.mkdir(parents=True,exist_ok=True)
    spec=importlib.util.spec_from_file_location('baseline_domain',D/'build_outer_shell.py')
    base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
    skin=params.get('skin_mm',1.2);plane=params.get('plane_mm',1.2)
    base.D=D/'.work'/f'outer-shell-{n}w-s{skin:g}-p{plane:g}';base.D.mkdir(parents=True,exist_ok=True)
    raw=base.D/f'print-material-{n}w.brep'
    if not raw.exists():base.build(n,skin,plane)
    shell=cq.importers.importBrep(str(raw)).val()
    body=cq.importers.importStep(str(SRC/'body-only.step')).val().translate((-250,-182,0)).rotate((0,0,0),(0,0,1),180)
    outline=layout.outline();wall=base.thickness(n)
    dense=layout.dense_region(outline,params);ribs=layout.rib_plane_region(outline,params)
    collar=layout.windows(params).buffer(wall,quad_segs=8)
    domain=shell.intersect(body)
    reinforcement=prism(dense.union(collar),0,24).intersect(body)
    domain=domain.fuse(reinforcement)
    saddles=[base.x_prism(profile,0,length) for label,profile,length in layout.tunnel_saddles(params)]
    for saddle in saddles:domain=domain.fuse(saddle.intersect(body))
    assert domain.isValid()
    if params['planes']=='shaped':
        air_xy=outline.buffer(-wall,quad_segs=8).difference(union_all([ribs,dense,collar]))
        keep=[base.x_prism(base.access_profile(y).buffer(wall,quad_segs=8),0,220) for y in base.FIXINGS]
        for z,z1 in layout.plate_bands(params)[1:-1]:
            air=prism(air_xy,z,z1-z).cut(*(keep+saddles))
            domain=domain.cut(air)
            assert domain.isValid(),z
    assert len(domain.Solids())==1
    before=domain.Volume();faces=len(domain.Faces());clean=domain.clean()
    assert clean.isValid() and len(clean.Solids())==1 and abs(clean.Volume()-before)<.001
    cq.exporters.export(clean,str(out/f'print-material-clean-{n}w.brep'))
    coupon=clean.intersect(cq.Solid.makeBox(10,24,24,cq.Vector(0,152,0))).clean()
    assert coupon.isValid() and len(coupon.Solids())==1
    cq.exporters.export(coupon,str(out/f'landing-{n}w.brep'))
    row={'revision':'F','parameters':params,'layout_sha256':layout.layout_hash(params),
         'body_STEP_sha256':hashlib.sha256((SRC/'body-only.step').read_bytes()).hexdigest(),
         'effective_wall_mm':wall,'volume_mm3':clean.Volume(),'valid':True,'solid_count':1,
         'cleanup':{'faces_before':faces,'faces_after':len(clean.Faces()),'volume_change_mm3':clean.Volume()-before},
         'model':f"Finished E13 perimeter/chamfer/tunnel guards intersected with Rev F body; new window collars and full-width dense regions; two {params['planes']} internal {plane:g} mm planes and {skin:g} mm broad skins; zero sparse-infill credit."}
    (out/f'geometry-{n}w.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps(row),flush=True)

if __name__=='__main__':main()
