"""Package reconstructed print controls with explicit reference and result scope."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import zipfile
from checkpoint_ef import clean, FILES

D = Path(__file__).resolve().parent
ROOT = D.parents[1]
CAD = ROOT / 'designs/rev-g2/print-controls'
RAW = D / '.work/print-controls'
PUBLIC = D / 'print-control-results'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checkpoint(name):
    cad, raw, out = CAD/name, RAW/name, PUBLIC/name
    out.mkdir(parents=True, exist_ok=True)
    params = json.loads((cad/'selected-layout.json').read_text())
    source = json.loads((cad/'source-verification.json').read_text())
    for file, expected in source['copied_files_sha256'].items():
        assert sha(cad/file) == expected, (name, file)
    slicing = json.loads((cad/'slice-verification.json').read_text())
    comparison = slicing['comparison_with_matched_P1S_G']['all_print_moving_extrusion_volume_mm3']
    assert slicing['object_paths_outside_bed'] == slicing['object_paths_intersecting_exclusion'] == 0
    assert slicing['material_connectivity']['connected_structural_components'] == 1
    with zipfile.ZipFile(cad/'slice-evidence.zip', 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for file in FILES:
            path = raw/'slice'/file
            if path.suffix == '.json':
                clean(json.loads(path.read_text()))
            info = zipfile.ZipInfo(file, date_time=(2026, 9, 11, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    # Preserve compact receipts from every attempt, including rejected solves.
    names = {'solve.json', 'completion.json', 'preparation.json', 'geometry.json',
             'interfaces.json', 'adaptive.json', 'shape-verification.json', 'audit.json'}
    audited = []
    for path in sorted(raw.rglob('*.json')):
        if path.name not in names:
            continue
        value = json.loads(path.read_text()); clean(value)
        target = out/path.relative_to(raw)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        if path.name == 'audit.json':
            solve = path.parent.parent/value['source_result']/'solve.json'
            if not solve.exists():
                continue
            result = json.loads(solve.read_text())
            assert value['status'] == result['status']
            tolerance = result['contact_history'][-1]['requested_linear_rtol']
            audited.append((tolerance, path, value))
            for file in ['g-results.png', 'projection.npz']:
                if (path.parent/file).exists():
                    shutil.copyfile(path.parent/file, target.parent/file)
    selected = min(audited, key=lambda item: item[0]) if audited else None
    saving = 100*(1-comparison['EF']/comparison['G'])
    report = dict(candidate=name, comparison_control='g-asa-8w-1p6',
                  spent_volume_mm3=comparison['EF'], reference_volume_mm3=comparison['G'],
                  saving_percent=saving, Orca_estimated_mass_g=slicing['Orca_estimated_filament_mass_g'],
                  polymer=params['filament_type'], walls=params['walls'], skin_mm=params['skin_mm'],
                  mechanics_status='PENDING',
                  scope='Deliberate G slicer controls, not the recovered successful ASA print. Recovery associates that print with E13, seven walls and 10 percent infill. No measured material calibration is claimed.')
    mechanics = 'Mechanical screening is pending.'
    if selected:
        tolerance, path, audit = selected
        report.update(mechanics_status=audit['status'], linear_rtol=tolerance,
                      maximum_resultant_displacement_mm=audit['maximum_resultant_displacement_mm'],
                      raw_tensile_peak=audit['raw_tensile_peak'],
                      geometry_omission_fraction=audit['geometry_omission_fraction'],
                      audit=path.relative_to(raw).as_posix())
        mechanics = (f"Retained-material contact screen at 12 kg: **{audit['maximum_resultant_displacement_mm']:.6f} mm** maximum movement, "
                     f"**{audit['raw_tensile_peak']['MPa']:.6f} MPa** raw tensile peak. Linear tolerance {tolerance:.0e}; "
                     f"{100*audit['geometry_omission_fraction']:.3f}% nominal material omitted. "
                     'Same uncalibrated isotropic 1 GPa planning law for all controls. No measured ASA/PETG modulus or strength is inferred.')
        if tolerance > 1e-5:
            mechanics += ' This is an intermediate diagnostic; the 1e-5 gate is not established. Failed tighter attempts remain recorded.'
    reserve = ''
    if params.get('cut_baseline') and params.get('direct_brace_core'):
        base = json.loads((CAD/params['cut_baseline']/'slice-verification.json').read_text())
        cut = base['comparison_with_matched_P1S_G']['all_print_moving_extrusion_volume_mm3']['EF']
        report.update(gross_cut_percent=100*(1-cut/comparison['G']), added_back_mm3=comparison['EF']-cut,
                      reserve_to_20_percent_target_mm3=.8*comparison['G']-comparison['EF'])
        reserve = (f"\nGross cut **{report['gross_cut_percent']:.3f}%**; added back **{report['added_back_mm3']/1000:.3f} cm3** "
                   f"as a continuous solid brace core; net saving **{saving:.3f}%**. "
                   f"Reserve before reaching the 20% target: {report['reserve_to_20_percent_target_mm3']/1000:.3f} cm3.\n")
    rawurl = 'https://raw.githubusercontent.com/thereprocase/spool-wall-rack/main/designs/rev-g2/print-controls/'+name
    helpers = '\n\n'.join(rawurl+'/'+helper+'.step' for helper in params['modifier_names'])
    text = f"""# {params['name']}

Implemented experimental CAD and actual Orca slice. Physical performance is unqualified.

Spent extrusion **{comparison['EF']/1000:.3f} cm3**, versus reconstructed G with eight walls and 1.6 mm skins at **{comparison['G']/1000:.3f} cm3**: **{saving:.3f}% less volume**. Orca estimates **{report['Orca_estimated_mass_g']:.2f} g** in {params['filament_type']}; this is not a weighed print. Cross-polymer volume savings are not mass savings.
{reserve}
{mechanics}

Recovered print evidence changes the physical reference: the overnight ASA archive has seven walls and 10% base infill, and its associated downloaded STEP matches E13 exactly. The newer downloaded STEP matches G; the saved PETG project has two walls, 10% base infill and all three dense helpers, but it was saved after the morning print began. Its exact submitted PETG slice is not recovered. These are deliberately controlled G schedules with 1.6 mm skins and unchanged G helpers, not replicas of the successful ASA print. Earlier EF savings used a separate two-wall, 1.0 mm skin digital G baseline. See the recovery receipt alongside these handoffs.

Use OrcaSlicer, P1S, 0.4 mm nozzle, **{params['walls']} walls**, **eight top and bottom layers at 0.2 mm**, **0% base infill**, and **100% infill for every supplied helper**. Only the body is a printable part. Import STEP parts aligned and assign modifier roles; STEP does not store those roles. The model-only 3MF records roles but does not calibrate a printer or filament. Slice archives are engineering evidence, not ready-to-print machine instructions.

Sacrificial 0.4 mm bridges count as spent plastic but receive zero stiffness, strength or bond credit. Actual credited material forms one component; geometric connectivity does not measure bond strength or ensure unsupported print quality. Rods, mounts, spool clearance and the 25.4 mm moulding locating underside remain fixed. Moulding supplies no assumed structural support.

Combined STEP

{rawurl}/bracket-with-modifiers.step

Body STEP

{rawurl}/body-only.step

Model-only 3MF

{rawurl}/{params['model_file']}

Individual helper STEPs

{helpers}

Actual slice and effective settings

{rawurl}/slice-evidence.zip

![Actual credited material sections](toolpath-sections.png)
"""
    (cad/'README.md').write_text(text)
    (out/'summary.json').write_text(json.dumps(report, indent=2)+'\n')
    manifest = {p.name:sha(p) for p in sorted(cad.iterdir()) if p.is_file() and p.name != 'SHA256SUMS.json'}
    (cad/'SHA256SUMS.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return report


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('candidates', nargs='*'); args = ap.parse_args()
    names = args.candidates or [p.name for p in sorted(CAD.iterdir()) if p.is_dir()]
    for name in names:
        print(json.dumps(checkpoint(name)), flush=True)


if __name__ == '__main__':
    main()
