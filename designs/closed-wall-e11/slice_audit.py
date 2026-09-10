"""Local OrcaSlicer structural-path audit; never send or start a print.

Equivalent whole-object height ranges represent the two full-plane helpers.
The generic 256 mm machine and neutral filament are not calibrated profiles.
"""
from pathlib import Path
import json,subprocess,sys
D=Path(__file__).resolve().parent

def main():
 walls=int(sys.argv[1]);assert walls in [8,10]
 exe=sys.argv[2] if len(sys.argv)>2 else 'orca-slicer'
 work=D/'.work';out=work/f'audit-{walls}w';out.mkdir(parents=True,exist_ok=True)
 data=work/'orca-audit-data';data.mkdir(exist_ok=True)
 # Standalone base presets: Orca's CLI matches their explicit names without
 # trying to resolve user-preset inheritance from an installed profile tree.
 common={'from':'system','version':'2.4.2.0','instantiation':'true'}
 machine={**common,'type':'machine','name':'E11 geometry audit 256mm',
  'printer_settings_id':'E11 geometry audit 256mm','printer_technology':'FFF',
  'gcode_flavor':'marlin','nozzle_diameter':['0.4'],
  'printable_area':['0x0','256x0','256x256','0x256'],'printable_height':'256',
  'machine_start_gcode':'M83\nG92 E0','machine_end_gcode':'',
  'layer_change_gcode':'G92 E0','nozzle_type':'hardened_steel'}
 process={**common,'type':'process','name':f'E11 {walls} wall structural audit',
  'print_settings_id':f'E11 {walls} wall structural audit','compatible_printers':[machine['name']],
  'layer_height':'0.2','initial_layer_print_height':'0.2','wall_loops':str(walls),
  'top_shell_layers':'6','bottom_shell_layers':'6','top_shell_thickness':'1.2','bottom_shell_thickness':'1.2',
  'sparse_infill_density':'15%','sparse_infill_pattern':'gyroid',
  'outer_wall_line_width':'0.42','inner_wall_line_width':'0.45','line_width':'0.45',
  'initial_layer_line_width':'0.45','internal_solid_infill_line_width':'0.45','top_surface_line_width':'0.45',
  'wall_generator':'arachne','detect_thin_wall':'0',
  'gap_fill_target':'everywhere','filter_out_gap_fill':'0',
  'brim_type':'no_brim','skirt_loops':'0','enable_support':'0',
  'infill_combination':'0','reduce_infill_retraction':'0','enable_arc_fitting':'0',
  'only_one_wall_top':'0','only_one_wall_first_layer':'0','spiral_mode':'0',
  'outer_wall_speed':'40','inner_wall_speed':'60','sparse_infill_speed':'60','internal_solid_infill_speed':'60',
  'top_surface_speed':'40','initial_layer_speed':'30','initial_layer_infill_speed':'30'}
 filament={**common,'type':'filament','name':'Neutral PLA geometry audit',
  'filament_settings_id':['Neutral PLA geometry audit'],'filament_id':'GFAUDIT',
  'filament_type':['PLA'],'filament_diameter':['1.75'],'filament_density':['1.24'],
  'filament_flow_ratio':['1'],'filament_max_volumetric_speed':['12'],
  'nozzle_temperature':['210'],'nozzle_temperature_initial_layer':['210']}
 for name,settings in [('machine',machine),('process',process),('filament',filament)]:
  (out/f'{name}.json').write_text(json.dumps(settings,indent=2))
 helpers=json.loads((D/'build-verification.json').read_text())['helpers']
 ranges=[{'min_z':h['z_min_mm'],'max_z':h['z_max_mm'],
          'range_params':{'layer_height':'0.2','sparse_infill_density':'100%','sparse_infill_pattern':'rectilinear'}} for h in helpers]
 assembly={'plates':[{'plate_name':f'E11 {walls} wall audit','need_arrange':True,
  'objects':[{'path':str(D/'body-only.stl'),'count':1,'filaments':[1],'height_ranges':ranges}]}]}
 (out/'assembly.json').write_text(json.dumps(assembly,indent=2))
 args=[exe,'--datadir',str(data),'--slice','0','--outputdir',str(out),
       '--load-settings',';'.join(str(out/f'{s}.json') for s in ['machine','process']),
       '--load-filaments',str(out/'filament.json'),'--load-assemble-list',str(out/'assembly.json'),
       '--export-3mf','audit.3mf','--export-settings',str(out/'effective-settings.json')]
 with (out/'orca.log').open('w',encoding='utf-8') as log:
  result=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT)
 assert result.returncode==0,('OrcaSlicer failed; inspect local audit log',result.returncode)
 assert all((out/name).exists() for name in ['audit.3mf','plate_1.gcode','effective-settings.json'])
 print(f'OrcaSlicer {walls}-wall audit complete; inspect_toolpaths.py checks the emitted paths',flush=True)

if __name__=='__main__':main()
