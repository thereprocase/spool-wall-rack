"""Add a direct hollow brace and reinvest in its bearing-to-keel junctions."""
from pathlib import Path
import hashlib,json,shutil,sys,time
import cadquery as cq
import numpy as np
from shapely.geometry import Point,LineString,shape,mapping,box
from shapely import union_all
D=Path(__file__).resolve().parent;BASE=D.parent/'ef-cut-v4';REFERENCE=D.parent/'ef-hybrid-v1'
sys.path.insert(0,str(REFERENCE));import build_cad as shared
sys.path.insert(0,str(D.parent/'shape-seeds'));import generate as seeds
from reinforcement import tapered_regions

def installed(p):return p.translate((-250,-182,0)).rotate((0,0,0),(0,0,1),180)
def main():
    start=time.perf_counter();params=json.loads((D/'selected-layout.json').read_text())
    geo=json.loads((BASE/'geometry.geojson').read_text());shapes={v['properties']['name']:shape(v['geometry']) for v in geo['features']}
    brace=LineString(params['direct_brace']['points_XY_mm']).buffer(params['direct_brace']['radius_mm'],quad_segs=16)
    outline=shapes['hybrid_body_projection'].union(brace);assert outline.is_valid and outline.geom_type=='Polygon'
    assert outline.intersection(seeds.moulding_keepout()).area<1e-7
    lip=LineString([(0,-32),(25.4,-32)]);assert outline.boundary.intersection(lip).length>25.4-1e-6
    clearance=[]
    for diameter in np.linspace(180,220,161):
        for radius in [12.4,12.7]:
            q=np.sqrt((diameter/2+radius)**2-10144/4);center=Point(140-12*q/np.sqrt(10144),6+100*q/np.sqrt(10144))
            clearance.append(outline.distance(center)-diameter/2)
    assert min(clearance)>3.5
    for v in geo['features']:
        if v['properties']['name']=='hybrid_body_projection':v['geometry']=mapping(outline)
    (D/'geometry.geojson').write_text(json.dumps(geo,separators=(',',':'))+'\n')
    projection=json.loads((BASE/'projection-verification.json').read_text());projection.update(status='PASS_NEW_BRACE_XY_GEOMETRY',projected_body_area_mm2=outline.area,minimum_sampled_nominal_spool_clearance_mm=min(clearance),new_brace_area_outside_prior_body_mm2=outline.difference(shapes['hybrid_body_projection']).area)
    projection['source_text_hashes']={'designs/rev-g2/ef-cut-v4/geometry.geojson':hashlib.sha256((BASE/'geometry.geojson').read_text().encode()).hexdigest()};(D/'projection-verification.json').write_text(json.dumps(projection,indent=2)+'\n')
    original=installed(cq.importers.importStep(str(BASE/'body-only.step')).val())
    body=original.fuse(shared.prism(brace,0,24)).clean()
    for y in shared.FIXINGS:
        body=body.cut(shared.x_prism(shared.access_profile(y),shared.LAND,250))
        bore=shared.access_profile(y,radius=2.6,roof_z=12+2.6*2**.5,round_top=0)
        body=body.cut(shared.x_prism(bore,-1,shared.LAND+1.01))
    body=body.clean();assert body.isValid() and len(body.Solids())==1
    mask=shared.prism(shapes['protected_G_interfaces'],-1,26)
    xor=body.intersect(mask).cut(original.intersect(mask)).Volume()+original.intersect(mask).cut(body.intersect(mask)).Volume();assert xor<1e-5
    moulding=body.intersect(cq.Solid.makeBox(25.4,968,26,cq.Vector(0,-1000,-1))).Volume();assert moulding<1e-6
    fixings=[]
    for y in shared.FIXINGS:
        ring=cq.Solid.makeCylinder(6.5,3.4,cq.Vector(.1,y,12),cq.Vector(1,0,0)).cut(cq.Solid.makeCylinder(2.75,3.4,cq.Vector(.1,y,12),cq.Vector(1,0,0)))
        fraction=body.intersect(ring).Volume()/ring.Volume();driver=body.intersect(shared.x_prism(shared.access_profile(y),shared.LAND+.01,250)).Volume();assert fraction>=.98 and driver<1e-6
        fixings.append(dict(axis_YZ_mm=[y,12],support_fraction=fraction,driver_overlap_mm3=driver))
    printed=shared.printed(body);cq.exporters.export(printed,str(D/'body-only.step'));cq.exporters.export(printed.copy(),str(D/'body-only.stl'),tolerance=.02,angularTolerance=.08)
    bodymesh=shared.repair_modifier(D/'body-only.stl',1);cq.exporters.export(body.copy(),str(D/'body-mounted.stl'),tolerance=.02,angularTolerance=.08);shared.repair_modifier(D/'body-mounted.stl',1)
    rt=cq.importers.importStep(str(D/'body-only.step')).val();assert rt.isValid() and len(rt.Solids())==1 and abs(rt.Volume()-body.Volume())<1e-3
    assembly=cq.Assembly(name='EF-DIRECT-BRACE-AND-MODIFIERS');assembly.add(printed,name='BODY-print');rows=[]
    # Retain the prior background dense helper; the added brace is hollow,
    # with the same two walls/skins and a central plate as the rest of the body.
    regions=tapered_regions(params);a,b=params['internal_plate_z_interval_mm']
    for name in params['modifier_names']:
        if name=='dense-chords-and-seats':
            for ext in ['.step','.stl']:shutil.copyfile(BASE/(name+ext),D/(name+ext))
            part=cq.importers.importStep(str(D/(name+'.step'))).val();helper=installed(part);mesh={'copied_from':'ef-cut-v4'}
        else:
            helper=shared.prism(outline.union(box(-16,105,1,115)),a,b-a) if name=='central-rib-plane' else shared.prism(union_all(regions),0,24)
            helper=helper.clean();assert helper.isValid();part=shared.printed(helper)
            cq.exporters.export(part,str(D/(name+'.step')));cq.exporters.export(part.copy(),str(D/(name+'.stl')),tolerance=.02,angularTolerance=.08);mesh=shared.repair_modifier(D/(name+'.stl'),len(helper.Solids()))
            rt=cq.importers.importStep(str(D/(name+'.step'))).val();assert rt.isValid() and abs(rt.Volume()-helper.Volume())<1e-3
        assembly.add(part,name=name+'-MODIFIER-100pct');rows.append(dict(name=name,solid_count=len(helper.Solids()),body_intersection_mm3=helper.intersect(body).Volume(),STL_check=mesh,role='100% infill modifier; never an additional printable part'))
        print('helper ready',name,flush=True)
    assembly.save(str(D/'bracket-with-modifiers.step'));rt=cq.importers.importStep(str(D/'bracket-with-modifiers.step')).val();assert len(rt.Solids())==1+sum(r['solid_count'] for r in rows) and all(s.isValid() for s in rt.Solids())
    r=dict(status='PASS_DIRECT_BRACE_CAD_AND_INTERFACE_CHECKS; PRINT_AND_MECHANICS_UNQUALIFIED',body_valid=True,body_solids=1,body_source='ef-cut-v4',added_body_CAD_volume_mm3=body.Volume()-original.Volume(),body_CAD_envelope_volume_mm3=body.Volume(),protected_interface_symmetric_difference_mm3=xor,crown_moulding_keepout_overlap_mm3=moulding,fixing_checks=fixings,fixed_rod_centers_XY_mm=[[90,0],[190,12]],helpers=rows,assembly_solid_count=len(rt.Solids()),body_STL_check=bodymesh,elapsed_seconds=time.perf_counter()-start,scope='The upper-mast relief is retained. A hollow diagonal joins the lower mounting region to the keel, bypassing the bent locating ledge. The original background dense helper is reused; added material is measured by a fresh slice. G interfaces and moulding constraints are independently checked.')
    (D/'cad-verification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2),flush=True)
if __name__=='__main__':main()
