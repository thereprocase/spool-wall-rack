"""Cross-check the E11 handoff and its published result fields.

Run with --write to record a new manifest after regenerating changed outputs.
Normal use verifies the recorded manifest and numerical consistency. This does
not rerun the CAD, mesher, solver, slicer, or physical qualification.
"""
from pathlib import Path
from urllib.parse import unquote
import hashlib,json,re,sys
import numpy as np
D=Path(__file__).resolve().parent;ROOT=D.parents[1]
CAD=ROOT/'designs/closed-wall-e11';MANIFEST=D/'release-verification.json'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def close(a,b,rtol=1e-8,atol=1e-8):assert np.allclose(a,b,rtol=rtol,atol=atol),(a,b)
def main():
 fields=[]
 for path in sorted(D.glob('*-results.json')):
  r=read(path);name=r['name'];data=np.load(D/f'{name}-solution.npz')
  p,t,u,vm,vol=(data[k] for k in ['p','t','u','vm','volume'])
  dim=p.shape[1];count_key='tetrahedra' if dim==3 else 'triangles'
  assert p.shape==u.shape and len(p)==r['nodes'] and len(t)==r[count_key]
  assert t.shape[1]==dim+1 and t.min()>=0 and t.max()<len(p)
  assert len(vol)==len(vm)==len(t) and np.all(vol>0)
  for key in data.files:assert np.isfinite(data[key]).all(),(name,key)
  peak_key='vm_max_MPa_not_allowable' if dim==3 else 'raw_vm_max_MPa_not_allowable'
  close(vm.max(),r[peak_key])
  sig=data['stress']
  if dim==3:
   expected=np.sqrt(.5*((sig[0,0]-sig[1,1])**2+(sig[1,1]-sig[2,2])**2+(sig[2,2]-sig[0,0])**2)+3*(sig[0,1]**2+sig[1,2]**2+sig[2,0]**2))
   assert r['contact_converged']
   for key in ['relative_free_residual','relative_force_balance_error','relative_moment_balance_error']:assert r[key]<1e-6
   close(vol.sum(),r['volume_mm3'])
   close(np.linalg.norm(u,axis=1).max(),r['max_displacement_mm_at_E1000'])
   q=read(D/f'{name}-mesh-quality.json');assert q['removed_absolute_volume_mm3']<1e-8
   assert len(t)==q['input_tetrahedra']-q['removed_numerically_degenerate_cells']
   tet=p[t];geovol=np.abs(np.linalg.det(tet[:,1:]-tet[:,:1]))/6
   close(geovol,vol,rtol=1e-6,atol=1e-9)
  else:
   expected=np.sqrt(sig[0,0]**2-sig[0,0]*sig[1,1]+sig[1,1]**2+3*sig[0,1]**2)
   assert r['relative_free_residual']<1e-6
   assert r['finished_STL_sha256']==sha(ROOT/f'designs/closed-wall-{r["revision"].lower()}/body-mounted.stl')
  close(vm,expected,rtol=1e-7)
  F=np.asarray(r['applied_force_N']);reaction=np.asarray(r['reaction_N'])
  assert np.linalg.norm(F+reaction)<1e-5
  assert np.linalg.norm(np.asarray(r['applied_moment_Nmm'])+np.asarray(r['reaction_moment_Nmm']))<1e-3
  fields.append({'name':name,'dimension':dim,'nodes':len(p),'elements':len(t),'relative_free_residual':r['relative_free_residual'],'raw_peak_MPa':float(vm.max())})
 assert len(fields)==16 and sum(f['dimension']==3 for f in fields)==6
 build=read(CAD/'build-verification.json');assert build['valid_body'] and build['body_solid_count']==1 and build['assembly_body_count']==3
 final=read(CAD/'final-finish-verification.json');assert final['delivered_body_valid'] and final['delivered_assembly_valid']
 assert len(final['finger_comparisons'])==36
 for row in final['finger_comparisons']:
  assert row['missing_beyond_0p025mm_mm2']<.001 and row['added_beyond_0p025mm_mm2']<.001
 sec=read(CAD/'section-verification.json')
 for case in sec['cases']:
  if case['revision']!='E11':continue
  for comparison in case['summary']['comparisons'].values():
   assert comparison['minimum_seat_I_ratio']>=sec['required_I_ratio']
   assert comparison['minimum_seat_Z_ratio']>=sec['required_Z_ratio']
 for n in [8,10]:
  g=read(D/f'geometry-{n}w.json');assert g['valid'] and g['solid_count']==1
  assert g['source_STEP_sha256']==sha(CAD/'body-only.step')
 paths=read(CAD/'toolpath-verification.json')
 for case in paths['cases']:
  assert case['body_STL_sha256']==sha(CAD/'body-only.stl')
  assert case['layer_count']==120 and case['solid_band_layer_count']==24
  assert case['minimum_seat_band_coverage']>.985 and case['minimum_seat_wall_coverage']>.96
  assert min(x['coverage_fraction'] for x in case['full_L_plane_checks'])>.985
  assert min(x['flexible_finger_footprint_coverage'] for x in case['finger_checks'])>.985
 for name in ['solver-verification.json','solver-verification3d.json']:
  v=read(D/name);assert v['patch_stress_error_MPa']<1e-8
  close(v['FE_energy_Nmm'],v['analytic_energy_Nmm'])
 summary=read(D/'engineering-summary.json')
 for case in summary['cases']:
  source=read(D/f'{case["source_mesh"]}-results.json')
  K=-1000*source['patches']['front_seat']['mean_displacement_mm_at_E1000'][1]
  close(K,case['front_K_MPa_mm']);close(K/case['reference_E_MPa'],case['initial_front_mm'])
 for row in summary['peak_diagnostics']:
  assert row['solution_sha256']==sha(D/f'{row["mesh"]}-solution.npz')
 # Record only published source, results and deliverables, excluding caches/logs.
 files=[ROOT/n for n in ['.gitignore','.gitattributes','AGENTS.md','README.md','DESIGN.md','DESIGN-JOURNAL.md','E10-ENGINEERING-GUIDE.md']]
 allowed={'.py','.scad','.svg','.stl','.step','.json','.png','.md','.txt'}
 for folder in [D,CAD]:
  files.extend(p for p in folder.iterdir() if p.is_file() and p!=MANIFEST and (p.suffix in allowed or p.name.endswith('-solution.npz')))
 artifacts=[];links=0
 for path in sorted(files):
  raw=path.read_bytes();is_text=path.suffix in {'.py','.scad','.svg','.json','.md','.txt'} or path.name.startswith('.git')
  payload=raw.replace(b'\r\n',b'\n') if is_text else raw
  artifacts.append({'path':path.relative_to(ROOT).as_posix(),'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest(),'normalization':'LF' if is_text else 'none'})
  if path.suffix=='.md':
   text=path.read_text(encoding='utf-8-sig')
   for url in re.findall(r'\]\(([^)]+)\)',text):
    if re.match(r'^[a-zA-Z]+:',url) or url.startswith('#'):continue
    target=unquote(url.split('#')[0].strip('<>'))
    assert (path.parent/target).exists(),(path.relative_to(ROOT),url)
    links+=1
 report={'revision':'E11','status':'Published-artifact and numerical consistency checks pass; physical qualification is unperformed','fields_checked':fields,'relative_markdown_links_checked':links,'artifact_hash_method':'SHA256; LF-normalize text as marked, preserve exact CAD/binary bytes','artifacts':artifacts}
 if '--write' in sys.argv:MANIFEST.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 else:
  previous=read(MANIFEST)
  assert previous['artifacts']==artifacts,'Published artifact hash mismatch; investigate changed files before writing a new manifest'
 print(json.dumps({'fields_checked':len(fields),'artifacts_checked':len(artifacts),'relative_markdown_links_checked':links,'status':'PASS'},indent=2))
if __name__=='__main__':main()
