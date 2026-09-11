"""Verify round-tripped modifier roles, alignment and actual extrusion footprints."""
from pathlib import Path
import sys,importlib.util,json,zipfile,hashlib,re,xml.etree.ElementTree as ET
import numpy as np
import shapely
from shapely.geometry import box
from scipy.spatial import cKDTree
import vtk
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
SCRIPT_DIR=Path(__file__).resolve().parent
D=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else SCRIPT_DIR
sys.path.insert(0,str(SCRIPT_DIR.parent/'closed-wall-e13'))
spec=importlib.util.spec_from_file_location('baseline_paths',SCRIPT_DIR.parent/'closed-wall-e13/inspect_toolpaths.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
sys.path.insert(0,str(SCRIPT_DIR))
import layout
from package_3mf import stl

def transform(text):return np.array(list(map(float,text.split()))).reshape(4,3)

def roundtrip(folder):
    checks=[]
    with zipfile.ZipFile(folder/'audit.3mf') as z:
        settings=ET.fromstring(z.read('Metadata/model_settings.config'))
        parts=settings.findall('object/part');assert len(parts)==4
        assert [p.attrib['subtype'] for p in parts]==['normal_part']+['modifier_part']*3
        model=ET.fromstring(z.read('3D/3dmodel.model'))
        components=model.findall('{*}resources/{*}object/{*}components/{*}component')
        assert len(components)==4
        for i,(part,component,name) in enumerate(zip(parts,components,['body-only','dense-chords-and-seats','rib-plane-lower','rib-plane-upper'])):
            metadata={m.attrib['key']:m.attrib['value'] for m in part.findall('metadata')}
            if i>0:assert metadata['sparse_infill_density']=='100%' and metadata['sparse_infill_pattern']=='rectilinear'
            source=next((v for k,v in component.attrib.items() if k.endswith('}path')),None)
            resource=ET.fromstring(z.read(source.lstrip('/'))) if source else model
            obj=next(o for o in resource.findall('{*}resources/{*}object') if o.attrib['id']==component.attrib['objectid'])
            pts=np.array([[float(v.attrib[k]) for k in 'xyz'] for v in obj.findall('{*}mesh/{*}vertices/{*}vertex')])
            xf=transform(component.attrib['transform']);pts=pts@xf[:3]+xf[3]
            original,_=stl(D/(name+'.stl'))
            delta=max(cKDTree(pts).query(original)[0].max(),cKDTree(original).query(pts)[0].max())
            assert delta<.0001,(name,delta)
            checks.append({'part':name,'role':part.attrib['subtype'],'maximum_roundtrip_vertex_error_mm':float(delta)})
    return checks

def main():
    params=json.loads((D/'selected-layout.json').read_text());walls=params['walls'];folder=D/'.work'/f'audit-{walls}w'
    alignment=roundtrip(folder)
    p,w,role,layer,xf=base.parse(folder)
    assert set(layer)==set(range(120))
    assert np.allclose(xf,np.array([[0,-1,0],[1,0,0],[0,0,1],[12.5,274.2465,0]]),atol=.001)
    settings=json.loads((folder/'effective-settings.json').read_text())
    skin=params.get('skin_mm',1.2);skin_layers=int(round(skin/.2));bands=layout.plate_bands(params)
    for k,v in [('wall_loops',walls),('top_shell_layers',skin_layers),('bottom_shell_layers',skin_layers)]:assert int(settings[k])==v
    for k in ['layer_height','initial_layer_print_height']:assert float(settings[k])==.2
    assert settings['sparse_infill_density']==f"{params['infill_percent']}%"
    assert settings['wall_generator']=='arachne' and settings['gap_fill_target']=='everywhere'
    reader=vtk.vtkSTLReader();reader.SetFileName(str(D/'body-only.stl'));reader.Update()
    # STL is stored in printer-oriented coordinates; convert to installed XY.
    tr=vtk.vtkTransform();tr.Translate(250,182,0);tr.RotateZ(180)
    tf=vtk.vtkTransformPolyDataFilter();tf.SetInputData(reader.GetOutput());tf.SetTransform(tr);tf.Update();mesh=tf.GetOutput()
    inside=vtk.vtkSelectEnclosedPoints();inside.Initialize(mesh)
    outline=layout.outline();dense=layout.dense_region(outline,params);ribs=layout.rib_plane_region(outline,params)
    thick=.42+(walls-1)*(.45-.2*(1-np.pi/4))
    # All skin/rib layers and representative layers of each intervening core.
    targets=[k for k in range(120) if any(a<(k+.5)*.2<b for a,b in bands)]+[9,19,29,49,59,69,89,99,109]
    rows=[];footprints={}
    for k in sorted(targets):
        z=(k+.5)*.2;poly=base.layer_polygons(mesh,z,inside)
        dense=layout.dense_at_z(outline,params,z)
        target=poly.difference(poly.buffer(-thick,quad_segs=8)).union(dense.intersection(poly))
        broad=z<skin or z>24-skin;internal=any(a<z<b for a,b in bands[1:-1])
        if broad:target=poly
        elif internal:target=target.union(ribs.intersection(poly))
        mask=(layer==k)&(role!='Sparse infill')
        footprint=base.union_footprints(p,w,mask)
        covered=target.intersection(footprint.buffer(.03)).area/target.area
        dense_target=dense.intersection(poly)
        dense_coverage=dense_target.intersection(footprint.buffer(.03)).area/dense_target.area
        missing=dense_target.difference(footprint.buffer(.03))
        pieces=list(missing.geoms) if hasattr(missing,'geoms') else [missing]
        gaps=[{'area_mm2':q.area,'centroid_mm':[q.centroid.x,q.centroid.y]}
              for q in sorted(pieces,key=lambda q:q.area,reverse=True)[:5] if q.area>.001]
        rows.append({'layer_number':k+1,'z_mid_mm':z,'broad_skin':broad,'internal_plane':internal,
                     'structural_footprint_coverage':covered,'dense_helper_coverage':dense_coverage,
                     'largest_missing_dense_footprints':gaps,
                     'roles':sorted(set(role[layer==k]))})
        footprints[k]=footprint
        print('layer',k+1,'coverage',round(covered,6),'dense',round(dense_coverage,6),flush=True)
    # Every extrusion endpoint is inside the body's XY extent, excluding all tabs.
    assert float(p[:,:,0].min())>-.03,('Selection tab printed',p[:,:,0].min())
    # Check every layer for extrusion centerlines crossing either intended window.
    window_core=layout.windows(params).buffer(-.3)
    starts=shapely.points(p[:,0]);ends=shapely.points(p[:,1]);mids=shapely.points(p.mean(1))
    assert not any(np.any(shapely.contains(window_core,pts)) for pts in [starts,ends,mids]),'Extrusion inside window'
    gcode=(folder/'plate_1.gcode').read_text()
    def footer(key):return float(re.search(r'; filament used \['+re.escape(key)+r'\] = ([0-9.]+)',gcode).group(1))
    report={'slicer':'OrcaSlicer 2.4.2','parameters':params,'layer_count':120,'roundtrip_parts':alignment,
            'gcode_sha256':hashlib.sha256((folder/'plate_1.gcode').read_bytes()).hexdigest(),
            'input_3MF_sha256':hashlib.sha256((D/'rev-g-model-and-modifiers.3mf').read_bytes()).hexdigest(),
            'printed_volume_cm3':footer('cm3'),'neutral_density_g_cm3':1.24,'neutral_printed_mass_g':footer('g'),
            'selection_tabs_printed':False,'window_extrusion_centerlines_detected':False,
            'footprint_rounding_allowance_mm':.03,'minimum_structural_coverage':min(r['structural_footprint_coverage'] for r in rows),
            'minimum_dense_helper_coverage':min(r['dense_helper_coverage'] for r in rows),'layers':rows,
            'limitations':'Nominal emitted bead footprints only; not physical proof of extrusion, bridges, adhesion or creep. Sparse infill receives zero FEA credit.'}
    report['passes_coverage_gates']=report['minimum_structural_coverage']>.96 and report['minimum_dense_helper_coverage']>.985
    report['status']='PASS' if report['passes_coverage_gates'] else 'FAIL: nominal footprint coverage'
    (D/'toolpath-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    fig,axes=plt.subplots(2,3,figsize=(15,11),layout='constrained',facecolor='#f3f1e9')
    images=[max(0,skin_layers//2),19,int(round((bands[1][0]+bands[1][1])/2/.2))-.5,59,int(round((bands[2][0]+bands[2][1])/2/.2))-.5,120-max(1,skin_layers//2)]
    for ax,k0 in zip(axes.flat,images):
        k=int(k0)
        mask=layer==k;colors=np.where(np.isin(role[mask],list(base.WALL_ROLES)),'#146f78',np.where(role[mask]=='Sparse infill','#bbb9b1','#c89032'))
        ax.add_collection(LineCollection(p[mask],colors=colors,linewidths=.32))
        ax.set(xlim=(-4,212),ylim=(-47,182),aspect='equal',title=f'Layer {k+1} / Z={(k+1)*.2:.1f} mm',xlabel='Projection (mm)',ylabel='Installed height (mm)',facecolor='#f3f1e9')
    fig.suptitle(f'Rev G / actual OrcaSlicer paths / {walls} walls',fontsize=19,fontweight='bold',color='#243d43')
    fig.supxlabel('Teal: walls and gap fill · gold: dense infill and bridge paths · gray: sparse infill (zero FEA credit).\nAngular windows stay empty; modifier tabs do not appear in the emitted paths.',fontsize=10,color='#344e53')
    fig.savefig(D/'toolpath-sections.png',dpi=170);plt.close(fig)
    assert report['minimum_structural_coverage']>.96,report['minimum_structural_coverage']
    assert report['minimum_dense_helper_coverage']>.985,report['minimum_dense_helper_coverage']
    print('Toolpath and modifier gates passed',flush=True)

if __name__=='__main__':main()
