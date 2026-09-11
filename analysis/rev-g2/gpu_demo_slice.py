"""Fresh, isolated Orca replay of G's existing geometry and verified settings.

Runs the installed Windows Orca CLI from WSL. No CAD regeneration or printer
communication is claimed. Original archives and audit folders are untouched.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import time
import zipfile
import xml.etree.ElementTree as ET


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def win(p):
    return subprocess.check_output(['wslpath','-w',str(p.resolve())],text=True).strip()


def installed_profile(root,name):
    """Flatten the installed Orca inheritance chain, recording source hashes."""
    matches = list(root.rglob(name+'.json'))
    assert len(matches) == 1,(name,len(matches))
    path = matches[0]
    profile = json.loads(path.read_text(encoding='utf-8-sig'))
    inherited,receipt = ({},[]) if not profile.get('inherits') else installed_profile(root,profile['inherits'])
    inherited.update(profile)
    inherited.pop('inherits',None)
    return inherited,receipt+[{'file':path.relative_to(root).as_posix(),'sha256':sha(path)}]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--orca',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--source',type=Path,default=Path('designs/rev-g2/g-recheck/2w-5layers'))
    ap.add_argument('--p1s-petg',action='store_true')
    args = ap.parse_args()
    source = args.source
    original = Path('designs/rev-g2/g-recheck/2w-5layers/.work/audit-2w')
    out = args.output
    assert not out.exists(),'Use a fresh output directory to retain previous attempts'
    out.mkdir(parents=True)
    data = out/'orca-data'
    data.mkdir()
    for name in ['machine.json','process.json','filament.json']:
        shutil.copyfile(original/name,out/name)
    profile_receipt = None
    if args.p1s_petg:
        profiles = args.orca.parent/'resources/profiles/BBL'
        machine,machine_receipt = installed_profile(profiles,'Bambu Lab P1S 0.4 nozzle')
        filament,filament_receipt = installed_profile(profiles,'Generic PETG @base')
        filament.update({'name':'G PETG analysis demo','filament_settings_id':['G PETG analysis demo'],
                         'instantiation':'true','version':'2.4.2.0',
                         'compatible_printers':[machine['name']]})
        process = json.loads((out/'process.json').read_text())
        process.update({'name':'G P1S PETG 2w 5-skin demo','print_settings_id':'G P1S PETG 2w 5-skin demo',
                        'compatible_printers':[machine['name']],'curr_bed_type':'Textured PEI Plate'})
        for name,value in [('machine',machine),('filament',filament),('process',process)]:
            (out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
        profile_receipt = {'machine':machine_receipt,'filament':filament_receipt,
                           'scope':'Installed P1S machine and generic PETG base inheritance; process calibration is not claimed.'}
    model = source/'rev-g-model-and-modifiers.3mf'
    report = {'status':'RUNNING','input_model_sha256':sha(model),'orca_executable_sha256':sha(args.orca),
              'source_geometry':'Supplied body and aligned helpers; source model identified by SHA256.',
              'cad_stage':'Existing input 3MF hashed; no new geometry generation.',
              'profile_receipt':profile_receipt,
              'settings_sha256':{name:sha(out/name) for name in ['machine.json','process.json','filament.json']}}
    (out/'replay.json').write_text(json.dumps(report,indent=2)+'\n')
    command = [str(args.orca),'--datadir',win(data),'--orient','0','--arrange','0','--slice','0',
               '--outputdir',win(out),'--load-settings',';'.join(win(out/name) for name in ['machine.json','process.json']),
               '--load-filaments',win(out/'filament.json'),'--export-3mf','audit.3mf',
               '--export-settings',win(out/'effective-settings.json'),win(model)]
    start = time.perf_counter()
    with (out/'orca.log').open('w') as log:
        result = subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    report['slice_wall_seconds'] = time.perf_counter()-start
    report['returncode'] = result.returncode
    if result.returncode == 0:
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parent))
        from plastic_shape import read_paths,layer_shapes,PlasticShape
        start = time.perf_counter()
        paths,accounting = read_paths(out)
        report['path_parse_seconds'] = time.perf_counter()-start
        original_paths,_ = read_paths(original)
        import numpy as np
        comparisons = {}
        for key in paths:
            comparisons[key] = bool(np.array_equal(paths[key],original_paths[key]))
        report['exact_path_replay'] = comparisons
        report['accounting'] = accounting
        report['gcode_sha256'] = sha(out/'plate_1.gcode')
        report['original_gcode_sha256'] = sha(original/'plate_1.gcode')
        report['effective_settings_sha256'] = sha(out/'effective-settings.json')
        report['original_effective_settings_sha256'] = sha(original/'effective-settings.json')
        # If every numeric path/role/mask agrees exactly, the original validated
        # raw polygon cache remains the same mechanical input. No need to
        # polygonize an identical slice again just to manufacture a timing.
        report['status'] = 'PASS_EXACT_PATH_REPLAY' if all(comparisons.values()) else 'FAIL_PATH_REPLAY'
        if args.p1s_petg:
            effective = json.loads((out/'effective-settings.json').read_text())
            expected = {'printer_model':'Bambu Lab P1S','filament_type':['PETG'],'nozzle_diameter':['0.4'],
                        'wall_loops':'2','top_shell_layers':'5','bottom_shell_layers':'5','sparse_infill_density':'0%'}
            report['effective_process_checks'] = {key:{'expected':value,'actual':effective.get(key),
                                                       'pass':effective.get(key) == value} for key,value in expected.items()}
            with zipfile.ZipFile(out/'audit.3mf') as archive:
                settings=ET.fromstring(archive.read('Metadata/model_settings.config'))
            parts=settings.findall('object/part')
            modifiers=[p for p in parts if p.get('subtype')=='modifier_part']
            modifier_values=[{m.get('key'):m.get('value') for m in p.findall('metadata')} for p in modifiers]
            roles_pass=(len(parts)==4 and len(modifiers)==3 and
                        sum(p.get('subtype')=='normal_part' for p in parts)==1 and
                        all(v.get('sparse_infill_density')=='100%' for v in modifier_values))
            report['actual_orca_modifier_roles']={'pass':roles_pass,'parts':len(parts),'modifiers':modifier_values}
            report['status'] = 'PASS_NEW_P1S_PETG_SLICE' if roles_pass and all(v['pass'] for v in report['effective_process_checks'].values()) else 'FAIL_EFFECTIVE_PROCESS'
            report['shape_cache_policy'] = 'New paths require a new raw cache and validation; historical cache is not substituted.'
    else:
        report['status'] = 'FAIL_ORCA'
    (out/'replay.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)
    if report['status'] not in ['PASS_EXACT_PATH_REPLAY','PASS_NEW_P1S_PETG_SLICE']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
