"""Neutral OrcaSlicer CLI audit of real multipart modifiers; never start a print."""
from pathlib import Path
import sys,json,subprocess
SCRIPT_DIR=Path(__file__).resolve().parent
D=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else SCRIPT_DIR

def main():
    exe=sys.argv[1];params=json.loads((D/'selected-layout.json').read_text())
    out=D/'.work'/f"audit-{params['walls']}w";out.mkdir(parents=True,exist_ok=True)
    data=D/'.work/orca-audit-data';data.mkdir(exist_ok=True)
    # Reuse precisely the E13 neutral process, machine and filament definitions.
    source=(SCRIPT_DIR.parent/'closed-wall-e13/slice_audit.py').read_text(encoding='utf-8')
    begin=source.index(" common={'from'");end=source.index(' helpers=json.loads')
    namespace={'out':out,'walls':params['walls'],'json':json}
    exec('if True:\n'+source[begin:end],namespace)
    process=json.loads((out/'process.json').read_text());process['sparse_infill_density']=f"{params['infill_percent']}%"
    process['name']=process['print_settings_id']=f"Rev G {params['walls']} wall neutral audit"
    skin=params.get('skin_mm',1.2)
    for key in ['top_shell_layers','bottom_shell_layers']:process[key]=str(int(round(skin/.2)))
    for key in ['top_shell_thickness','bottom_shell_thickness']:process[key]=str(skin)
    (out/'process.json').write_text(json.dumps(process,indent=2))
    args=[exe,'--datadir',str(data),'--orient','0','--arrange','0','--slice','0','--outputdir',str(out),
          '--load-settings',';'.join(str(out/f'{s}.json') for s in ['machine','process']),
          '--load-filaments',str(out/'filament.json'),
          '--export-3mf','audit.3mf','--export-settings',str(out/'effective-settings.json'),
          str(D/'rev-g-model-and-modifiers.3mf')]
    with (out/'orca.log').open('w',encoding='utf-8') as log:
        result=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT)
    assert result.returncode==0,('OrcaSlicer failed; inspect local audit log',result.returncode)
    assert all((out/name).exists() for name in ['audit.3mf','plate_1.gcode','effective-settings.json'])
    print('Rev G real-modifier audit sliced',flush=True)

if __name__=='__main__':main()
