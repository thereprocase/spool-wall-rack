"""Matched plane-stress screening of manufacturable Rev F layouts.

Voids are real holes in the mesh, not removed finite stress cells. Material
layers include the new window mouth chamfers, outer walls, broad skins,
selected rib planes and full-width solid-infill regions. Sparse infill has
zero stiffness credit; its nominal volume is included only in the mass proxy.
"""
from pathlib import Path
import sys,json,hashlib
import numpy as np
from shapely import from_wkb
import gmsh
D=Path(__file__).resolve().parent;ROOT=D.parents[1]
sys.path.insert(0,str(ROOT/'designs/rev-f'))
import layout
sys.path.insert(0,str(D.parent/'e13'))
import solve_comparison as solver
WORK=D/'.work';WORK.mkdir(exist_ok=True)
old_outline=solver.outline

def mesh_with_holes(poly,h):
    gmsh.initialize();gmsh.option.setNumber('General.Terminal',0);gmsh.model.add('rev-f')
    loops=[]
    for ring in [poly.exterior,*poly.interiors]:
        points=[gmsh.model.geo.addPoint(x,y,0,h) for x,y in list(ring.coords)[:-1]]
        lines=[gmsh.model.geo.addLine(a,b) for a,b in zip(points,points[1:]+points[:1])]
        loops.append(gmsh.model.geo.addCurveLoop(lines))
    gmsh.model.geo.addPlaneSurface(loops);gmsh.model.geo.synchronize()
    gmsh.option.setNumber('Mesh.MeshSizeMin',.25);gmsh.option.setNumber('Mesh.MeshSizeMax',h)
    gmsh.model.mesh.generate(2)
    tags,p,_=gmsh.model.mesh.getNodes();p=np.array(p).reshape(-1,3)[:,:2]
    kinds,_,cells=gmsh.model.mesh.getElements(2);t=np.array(cells[list(kinds).index(2)]).reshape(-1,3)
    lookup=np.zeros(int(tags.max())+1,dtype=int);lookup[tags]=np.arange(len(tags));t=lookup[t]
    gmsh.finalize();used,inv=np.unique(t,return_inverse=True)
    return p[used],inv.reshape(-1,3)

def material_layers(params):
    record=json.loads((D/'inputs/e13-layer-outlines.json').read_text(encoding='utf-8'))
    source=ROOT/'designs/closed-wall-e13/body-mounted.stl'
    assert record['stl_sha256']==hashlib.sha256(source.read_bytes()).hexdigest()
    outlines=[from_wkb(bytes.fromhex(s)) for s in record['wkb_hex']]
    exterior=old_outline('e13');rib=layout.rib_plane_region(exterior,params)
    walls=params['walls'];width=.42+(walls-1)*(.45-.2*(1-np.pi/4))
    layers=[];material_volume=0.;envelope_volume=0.
    for k,outline in enumerate(outlines):
        z=(k+.5)*.2;poly=outline.difference(layout.windows_at_z(params,z))
        bands=layout.plate_bands(params);dense=layout.dense_at_z(exterior,params,z)
        outer_skin=z<bands[0][1] or z>bands[-1][0]
        internal_plate=any(a<z<b for a,b in bands[1:-1])
        if outer_skin:solid=poly
        else:
            solid=poly.difference(poly.buffer(-width,quad_segs=12)).union(poly.intersection(dense))
            if internal_plate:solid=solid.union(poly.intersection(rib))
        assert solid.is_valid
        layers.append(solid)
        material_volume+=solid.area*.2;envelope_volume+=poly.area*.2
    return layers,{'structural_layer_volume_mm3':material_volume,'body_envelope_volume_mm3':envelope_volume,
        'nominal_print_volume_mm3':material_volume+(envelope_volume-material_volume)*params.get('infill_percent',10)/100,
        'new_void_area_mm2':layout.windows(params).area,'layout_sha256':layout.layout_hash(params)}

def screen(params,h=2,load_cases=('full',)):
    name=params['name'];folder=WORK/name;folder.mkdir(exist_ok=True)
    layers,metrics=material_layers(params)
    outline=old_outline('e13').difference(layout.windows(params))
    assert outline.geom_type=='Polygon' and outline.is_valid
    solver.D=folder;solver.material_layers=lambda revision,walls:(layers,metrics['layout_sha256'])
    solver.outline=lambda revision:outline;solver.mesh_outline=mesh_with_holes
    row={'name':name,'parameters':params,**metrics,'mesh_h_mm':h,'load_cases':{}}
    for load_case in load_cases:
        result=solver.solve(name,params['walls'],h,load_case)
        field=np.load(folder/f'{name}-{params["walls"]}w-h{h:g}-{load_case}-solution.npz')
        sig=field['stress'];energy=(sig[0,0]**2+sig[1,1]**2-2*.35*sig[0,0]*sig[1,1]+2*1.35*sig[0,1]**2)/(2*1000)
        row['load_cases'][load_case]={'front_movement_mm_at_E1000':-result['patches']['front_seat']['mean_displacement_mm_at_E1000'][1],
            'rear_movement_mm_at_E1000':-result['patches']['rear_seat']['mean_displacement_mm_at_E1000'][1],
            'load_compliance_Nmm_at_E1000':float(2*(energy*field['volume']).sum()),
            'raw_peak_tensile_MPa':float(field['principal'].max()),
            'raw_peak_VM_MPa':float(field['vm'].max()),'relative_free_residual':result['relative_free_residual']}
    (folder/'screen.json').write_text(json.dumps(row,indent=2)+'\n')
    (folder/f'screen-h{h:g}.json').write_text(json.dumps(row,indent=2)+'\n')
    return row

if __name__=='__main__':
    common={'walls':4,'window_scale':1.,'bottom_band':4.,'diagonal_band':4.,'seat_band':7.,'front_seat_band':3.,'planes':'full','infill_percent':10}
    candidates=[]
    for dense in [3.,4.,5.,6.]:
        candidates.append({**common,'name':f'f-chords-{dense:g}','bottom_band':dense,'diagonal_band':dense})
    for scale in [.75,1.15]:
        candidates.append({**common,'name':f'f-window-{scale:g}','window_scale':scale,'bottom_band':5.,'diagonal_band':5.})
    for frame in [4.,6.]:
        candidates.append({**common,'name':f'f-rib-planes-{frame:g}','planes':'shaped','rib_frame':frame,'bottom_band':5.,'diagonal_band':5.})
    candidates.append({**common,'name':'f-upper-window','upper_window':True,'bottom_band':5.,'diagonal_band':5.})
    rows=[]
    for params in candidates:
        row=screen(params);rows.append(row)
        print('SCREEN',json.dumps(row),flush=True)
        (D/'screening.json').write_text(json.dumps(rows,indent=2)+'\n')
