"""Publishable receipts for implemented EF CAD and actual-slice trials."""
from pathlib import Path
import argparse,hashlib,json,shutil,zipfile
D=Path(__file__).resolve().parent; ROOT=D.parents[1]
PUBLIC=D/'ef-hybrid-results'
FILES=['audit.3mf','plate_1.gcode','effective-settings.json','machine.json','process.json','filament.json','replay.json']

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def clean(value):
    if isinstance(value,str):
        assert not any(v in value.lower() for v in ['/mnt/','/home/','f:\\','c:\\users\\']),value[:120]
    elif isinstance(value,dict):
        for v in value.values():clean(v)
    elif isinstance(value,list):
        for v in value:clean(v)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--candidate',required=True);ap.add_argument('--attempt',type=Path,required=True);ap.add_argument('--result',default='solve');ap.add_argument('--audit',default='audit');args=ap.parse_args()
    cad=ROOT/'designs/rev-g2'/args.candidate;out=PUBLIC/args.candidate;out.mkdir(parents=True,exist_ok=True)
    params=json.loads((cad/'selected-layout.json').read_text());folder=args.attempt
    with zipfile.ZipFile(cad/'slice-evidence.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in FILES:
            p=folder/'slice'/name
            if p.suffix=='.json':clean(json.loads(p.read_text()))
            info=zipfile.ZipInfo(name,date_time=(2026,9,11,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,p.read_bytes())
    sources=['pipeline.json','shape/shape-verification.json','geometry/geometry.json','geometry/interfaces.json','adaptive/adaptive.json']
    for name in sources:
        p=folder/name
        if p.exists():
            clean(json.loads(p.read_text()));target=out/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    for result in ['solve','retry-coarse4','contact-discovery','contact-tight']:
        p=folder/result/'solve.json'
        if p.exists():
            clean(json.loads(p.read_text()));target=out/result/'solve.json';target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    audit=folder/args.audit/'audit.json';accepted=None
    if audit.exists():
        accepted=json.loads(audit.read_text());clean(accepted)
        for name in ['audit.json','g-results.png','projection.npz']:shutil.copyfile(folder/args.audit/name,out/name)
    s=json.loads((cad/'slice-verification.json').read_text());comp=s['comparison_with_matched_P1S_G']['all_print_moving_extrusion_volume_mm3'];saving=-comp['change_percent']
    printed=comp['EF']/1000;baseline=comp['G']/1000
    mechanics='Numerical screening is pending. Sliced mass and CAD checks are not a load rating.'
    if accepted:
        mechanics=(f"Retained-material contact screen: {accepted['maximum_resultant_displacement_mm']:.6f} mm maximum movement and {accepted['raw_tensile_peak']['MPa']:.6f} MPa raw tensile peak at 12 kg. "
                   f"Status: {accepted['status']}. Material omission: {100*accepted['geometry_omission_fraction']:.3f}%. "
                   'All finite stress samples and failed attempts remain preserved. Isotropic planning properties, boundary omission and physical qualification remain unresolved.')
    reinvest=''
    if params.get('cut_baseline'):
        cut=json.loads((cad.parent/params['cut_baseline']/'slice-verification.json').read_text())['comparison_with_matched_P1S_G']['all_print_moving_extrusion_volume_mm3']
        reinvest=f"\nGross cut: {-cut['change_percent']:.3f}% of G. Added back: {(comp['EF']-cut['EF'])/1000:.3f} cm3, or {100*(comp['EF']-cut['EF'])/comp['G']:.3f} percentage points of G. Net saving: {saving:.3f}%.\n"
    url='https://github.com/thereprocase/spool-wall-rack/tree/main/designs/rev-g2/'+args.candidate
    raw='https://raw.githubusercontent.com/thereprocase/spool-wall-rack/main/designs/rev-g2/'+args.candidate
    model=params.get('model_file','rev-g-model-and-modifiers.3mf')
    helpers=params.get('modifier_names',['dense-chords-and-seats','rib-plane-lower','rib-plane-upper'])
    text=f'''# {params['name']}

Implemented experimental CAD and actual Orca slice. Physical print and strength are unqualified.

Spent extrusion is **{printed:.3f} cm3**, versus matched P1S G at {baseline:.3f} cm3: **{saving:.3f}% less**. This includes sacrificial bridges and startup extrusion; it is not CAD volume or a weighed print.
{reinvest}
{mechanics}

The body retains the verified E+F outer geometry. Its protected G bearing and capture geometry has zero CAD symmetric difference. Mounting axes stay fixed, washer-land support is 99.08%, and driver clearance is checked. The locating underside stays at Y=-32 mm for the first 25.4 mm from the wall. Moulding supplies no assumed structural support.

Use OrcaSlicer, P1S, 0.4 mm nozzle, calibrated PETG or ASA, two walls, {round(params['skin_mm']/.2)} top/bottom layers at 0.2 mm, zero base infill and 100% rectilinear helpers. This receipt is the PETG slice; ASA requires a fresh process check. Import one object with aligned parts. Only the body prints. Every helper and its external tabs/halos must remain an infill modifier. STEP preserves alignment but does not encode slicer roles. The model-only 3MF records roles but carries no printer/filament calibration. The slice archive is engineering evidence, not machine-ready G-code.

Sacrificial 0.4 mm bridges count as spent plastic and receive zero structural or bond credit. Nominal credited paths form one connected component; that is not a guarantee of successful unsupported printing.

Combined STEP

{raw}/bracket-with-modifiers.step

Body STEP

{raw}/body-only.step

Model-only 3MF

{raw}/{model}

Individual helper STEPs

'''+''.join(raw+'/'+v+'.step\n\n' for v in helpers)+f'''Actual slice and effective settings

{raw}/slice-evidence.zip

All files and verification receipts

{url}

![Actual credited material sections](toolpath-sections.png)
'''
    (cad/'README.md').write_text(text)
    manifest={p.name:sha(p) for p in sorted(cad.iterdir()) if p.is_file() and p.name!='SHA256SUMS.json'}
    (cad/'SHA256SUMS.json').write_text(json.dumps(manifest,indent=2)+'\n')
    report=dict(candidate=args.candidate,spent_volume_mm3=comp['EF'],G_spent_volume_mm3=comp['G'],saving_percent=saving,
                mechanics_status=accepted['status'] if accepted else 'PENDING',scope='CAD, slicer and numerical evidence remain separate from physical qualification.')
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
