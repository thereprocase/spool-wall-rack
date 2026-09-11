"""Audit the search ledger, retained fields, geometry response and frame mapping."""
from pathlib import Path
import argparse,hashlib,json,tempfile,zipfile
import numpy as np
from evo_screen import Screen,BASE,GENES
from evo_search import ident,seed_change
from evo_transfer import transfer
from plastic_shape import read_paths


def parser_fixture(folder,offset):
    folder.mkdir()
    with zipfile.ZipFile(folder/'audit.3mf','w') as z:
        z.writestr('3D/3dmodel.model','<model><build><item transform="1 0 0 0 1 0 0 0 1 0 0 0"/></build></model>')
    area=np.pi*1.75**2/4
    (folder/'plate_1.gcode').write_text(f'''; filament_diameter: 1.75
; extruder_offset = 0x{offset}
; filament used [cm3] = {area*.3/1000}
G90
M83
;Z:0.2
G1 X0 Y{-offset} Z0.2
; printing object fixture
;TYPE:Outer wall
;WIDTH:0.45
;HEIGHT:0.2
G1 X1 Y{-offset} E0.1
;TYPE:Bridge
;HEIGHT:0.4
G1 X2 Y{-offset} E0.2
; stop printing object fixture
''')
    return read_paths(folder,np.c_[np.eye(3),np.zeros(3)])


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--batch',type=Path,required=True);ap.add_argument('--cache',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();assert not args.output.exists()
    ledger=json.loads((args.batch/'ledger.json').read_text());summary=json.loads((args.batch/'summary.json').read_text())
    records=ledger['records'];base=np.array([BASE[k] for k in GENES]);parents={ident(base.tolist()):base}
    assert len(records)==100 and len({r['id'] for r in records})==100
    assert np.array_equal(np.bincount([r['generation'] for r in records]),[25]*4)
    retained=0
    for row in records:
        values=np.array(row['values']);assert row['id']==ident(row['values'])
        assert np.all(values>=base*.8-1e-9) and np.all(values<=base*1.2+1e-9)
        assert np.max(abs(values/.05-np.rint(values/.05)))<1e-9
        ancestors=np.array([parents[p] for p in row['parents']])
        difference=abs(values/ancestors-1)
        valid=(difference<1e-9)|((difference>=.05-1e-9)&(difference<=.1+1e-9))
        assert valid.any(axis=0).all(),'Gene not inherited or changed by 5-10 percent'
        minimum_changes=np.count_nonzero((difference>1e-9).all(axis=0));assert minimum_changes<=3
        parameters=row['result']['parameters'];assert parameters['walls']==2 and parameters['infill_percent']==0
        field=args.batch/row['id']/'fields.npz'
        assert hashlib.sha256(field.read_bytes()).hexdigest()==row['all_fields_sha256']
        with np.load(field) as data:
            assert all(np.isfinite(data[k]).all() for k in data.files)
            assert data['stress'].shape==(2,2,37985) and data['principal'].shape==(37985,)
            assert np.all(data['volume']>0)
            assert data['principal'].max()==row['result']['raw_peak_tensile_MPa']
            retained+=len(data['principal'])
        parents[row['id']]=values
    model=Screen(args.cache)
    monotonic=[]
    for key in GENES:
        for sign in [-1,1]:
            volume=model.candidate_volume({**BASE,key:seed_change(BASE[key],sign)})
            assert (sign*(volume-model.volume)).min()>=-1e-9
            monotonic.append({'gene':key,'direction':sign,'material_change_mm3':float((volume-model.volume).sum())})
    with tempfile.TemporaryDirectory() as name:
        a,ra=parser_fixture(Path(name)/'zero',0);b,rb=parser_fixture(Path(name)/'shifted',2)
        assert all(np.array_equal(a[k],b[k]) for k in a)
        assert a['structural'].tolist()==[True,False]
        assert ra['relative_extrusion_footer_difference']<1e-12
    old=np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1],[1,0,0]])
    new=np.array([[0.,0,0],[1,0,0],[0,0,1],[2,0,0]])
    values,tr=transfer(old,new,old*2+1,np.ones(3))
    assert np.array_equal(values[:3],new[:3]*2+1) and np.array_equal(values[3],old[1]*2+1)
    assert tr['nearest_guesses']==1 and tr['ambiguous_split_coordinate_guesses']==1
    report={'status':'PASS_SEARCH_AND_TRANSFER_CHECKS','unique_proposals':100,'generations':[25]*4,
            'every_finite_candidate_stress_retained':retained,'raw_field_hashes_verified':100,
            'bounded_mutation_and_inheritance_checks':True,'positive_material_and_monotonic_helper_checks':monotonic,
            'extruder_offset_fixture_identical_installed_paths':True,'bridge_fixture_zero_structural_credit':True,
            'initial_guess_transfer_fixture':tr,'screen_elapsed_seconds':summary['elapsed_seconds'],
            'scope':'Implementation, mutation, numerical field and throughput checks. Predictive ranking requires subsequent actual-slice 3D comparisons.'}
    args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
