"""Actual Orca extrusion, placement and section receipts for the EF prototype."""
from pathlib import Path
import argparse
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

D=Path(__file__).resolve().parent; ROOT=D.parents[2]
sys.path.insert(0,str(ROOT/'analysis/rev-g2'))
from plastic_shape import PlasticShape
sys.path.insert(0,str(D.parent/'shape-seeds'))
import generate as seeds


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--attempt',type=Path,required=True)
    ap.add_argument('--output',type=Path,default=D)
    ap.add_argument('--baseline-shape',type=Path)
    ap.add_argument('--label',default='E + F')
    args=ap.parse_args(); folder=args.attempt; output=args.output
    replay=json.loads((folder/'slice/replay.json').read_text())
    assert replay['status'] in ['PASS_NEW_P1S_PETG_SLICE','PASS_NEW_P1S_ASA_SLICE']
    material=PlasticShape.load(folder/'shape')
    data=np.load(folder/'shape/extrusion-paths.npz')
    with zipfile.ZipFile(folder/'slice/audit.3mf') as z:
        model=ET.fromstring(z.read('3D/3dmodel.model'))
    xf=np.array([float(v) for v in model.find('{*}build/{*}item').get('transform').split()]).reshape(4,3)
    installed=np.zeros((len(data['paths']),2,3)); installed[:,:,:2]=data['paths']
    installed[:,:,2]=data['top'][:,None]
    model_points=installed.copy(); model_points[:,:,0]=250-installed[:,:,0]; model_points[:,:,1]=182-installed[:,:,1]
    bed=model_points@xf[:3]+xf[3]
    radius=data['width']/2
    lower=bed[:,:,:2].min(axis=1)-radius[:,None]; upper=bed[:,:,:2].max(axis=1)+radius[:,None]
    outside=(lower<0).any(axis=1)|(upper>256).any(axis=1)
    excluded=(lower[:,0]<18)&(upper[:,0]>0)&(lower[:,1]<28)&(upper[:,1]>0)
    assert not outside.any() and not excluded.any()
    assert material.report['bond_connectivity']['connected_structural_components']==1
    baseline_file=args.baseline_shape/'shape-verification.json' if args.baseline_shape else ROOT/'analysis/rev-g2/evolution-results/batch-02/p1s-baseline/shape-verification.json'
    baseline=json.loads(baseline_file.read_text())
    filament=json.loads((folder/'slice/filament.json').read_text())
    polymer=replay['effective_process_checks']['filament_type']['actual'][0]
    walls=replay['effective_process_checks']['wall_loops']['actual']
    keys=['all_print_moving_extrusion_volume_mm3','structurally_credited_extrusion_volume_mm3',
          'sacrificial_thick_bridge_extrusion_volume_mm3','nominal_footprint_union_volume_mm3']
    comparison={key:dict(G=baseline[key],EF=material.report[key],change_percent=100*(material.report[key]/baseline[key]-1)) for key in keys}
    gcode=(folder/'slice/plate_1.gcode').read_text()
    mass=float(re.search(r'^; filament used \[g\] = ([\d.]+)',gcode,re.MULTILINE).group(1))
    record=dict(status='PASS_ACTUAL_SLICE_PROCESS_AND_BED_CHECKS; PHYSICAL_PRINT_UNQUALIFIED',
                effective_process_checks=replay['effective_process_checks'],
                actual_orca_modifier_roles=replay['actual_orca_modifier_roles'],
                deposited_object_bed_bounds_with_nominal_width_mm=[*lower.min(axis=0),*upper.max(axis=0)],
                object_paths_outside_bed=int(outside.sum()),object_paths_intersecting_exclusion=int(excluded.sum()),
                bed_exclusion_rect_mm=[0,0,18,28],object_path_count=len(radius),
                coordinate_note='Deposited bed coordinates restored from parsed installed paths through the actual 3MF placement. Nozzle offset is already corrected by the material parser.',
                material_connectivity=material.report['bond_connectivity'],comparison_with_matched_P1S_G=comparison,
                Orca_estimated_filament_mass_g=mass,
                estimated_mass_note=f'Orca estimate using Generic {polymer} density {filament["filament_density"][0]} g/cm3; not a weighed print.',
                scope='Nominal deposited paths, effective settings, modifier roles, bed clearance and geometric connectivity. Unsupported-roof quality, physical fit, warm material behavior and strength are not certified.')
    record['comparison_reference_shape_sha256']=__import__('hashlib').sha256(baseline_file.read_bytes()).hexdigest()
    record['comparison_reference_note']='Explicitly supplied control shape' if args.baseline_shape else 'Historical P1S G, two walls and 1.0 mm skins'
    (output/'slice-verification.json').write_text(json.dumps(record,indent=2)+'\n')
    fig,axes=plt.subplots(1,3,figsize=(15,6),facecolor='#f4f2ed',layout='constrained')
    for ax,z in zip(axes,[3.1,8.1,12.1]):
        layer=next(raw for a,b,raw,simple in material.layers if a <= z < b)
        ax.set_facecolor('#f4f2ed'); seeds.envelope.draw(ax,layer,'#347c81',edgecolor='none')
        ax.set(aspect='equal',xlim=(-3,212),ylim=(-63,180),title=f'Actual credited plastic / Z = {z:.1f} mm')
        ax.set_xlabel('Projection from wall / mm'); ax.set_ylabel('Height / mm')
        ax.spines[['top','right']].set_visible(False)
    fig.suptitle(f'{args.label} / actual P1S {polymer} sliced material',fontsize=18,fontweight='bold')
    layers=replay['effective_process_checks']['top_shell_layers']['actual']
    modifiers=len(replay['actual_orca_modifier_roles']['modifiers'])
    fig.supxlabel(f'{walls} walls · {layers} top/bottom layers · zero base infill · {modifiers} 100% modifier parts\nSacrificial 0.4 mm bridges are excluded from these structural sections and receive no bond or stiffness credit.',fontsize=10)
    fig.savefig(output/'toolpath-sections.png',dpi=160);plt.close(fig)
    print(json.dumps(record,indent=2),flush=True)


if __name__=='__main__': main()
