"""Retain and integrate every saved stress sample into an EF strain-energy map."""
from pathlib import Path
import argparse,json
import numpy as np

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--result',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    r=json.loads((args.result/'solve.json').read_text());assert r['status'].startswith(('CONTACT_SCREEN','PASS_CONTACT'))
    with np.load(args.run/'geometry/geometry.npz') as d:p,spacing=d['p'],d['spacing']
    with np.load(args.run/'adaptive/adaptive.npz') as d:t,scale=d['t'],d['scale']
    low=np.floor(p[:,:2].min(axis=0)/2)*2;shape=np.ceil((p[:,:2].max(axis=0)-low)/2).astype(int)+1
    energy=np.zeros(shape);volume=np.zeros(shape);peak=np.full(shape,-np.inf);total=0;count=0
    E=r['planning_E_MPa'];nu=r['planning_nu']
    zones={'upper_mast_Y_above_60':0.,'wall_brace_root_X_below_30_Y_20_55':0.,'seat_forearm_X_95_130_Y_below_0':0.,'keel_post_X_75_95_Y_below_minus25':0.}
    for f in r['stress_fields']:
        s=np.load(args.result/f['file']);assert np.isfinite(s).all();n=len(s);first=f['first_leaf'];sc=scale[first:first+n]
        sq=(s[:,:,:3]**2).sum(axis=2)+2*(s[:,:,3:]**2).sum(axis=2);tr=s[:,:,:3].sum(axis=2)
        density=((1+nu)*sq-nu*tr**2)/(2*E);assert density.min()>=-1e-12
        vol=np.prod(spacing)*sc.astype(float)**3;en=density.mean(axis=1)*vol
        xyz=p[t[first:first+n,0]]+.5*spacing*sc[:,None];xy=np.floor((xyz[:,:2]-low)/2).astype(int)
        np.add.at(energy,(xy[:,0],xy[:,1]),en);np.add.at(volume,(xy[:,0],xy[:,1]),vol);np.maximum.at(peak,(xy[:,0],xy[:,1]),density.max(axis=1))
        x,y=xyz[:,0],xyz[:,1]
        for name,mask in zip(zones,[y>60,(x<30)&(y>20)&(y<55),(x>95)&(x<130)&(y<0),(x>75)&(x<95)&(y<-25)]):zones[name]+=float(en[mask].sum())
        total+=float(en.sum());count+=s.shape[0]*s.shape[1]
    assert count==len(t)*8
    indices=np.dstack(np.unravel_index(np.argsort(energy.ravel())[-30:][::-1],energy.shape))[0]
    summary=dict(source_result=args.result.name,source_status=r['status'],total_strain_energy_Nmm=total,retained_samples=count,zones_energy_fraction={k:v/total for k,v in zones.items()},highest_energy_bins=[dict(XY_center_mm=(low+(ij+.5)*2).tolist(),energy_Nmm=float(energy[tuple(ij)]),volume_mm3=float(volume[tuple(ij)])) for ij in indices],scope='Current isotropic retained-material load case. Integrated stress-derived strain energy, not a strength rating or a finite-removal sensitivity. Low energy alone does not clear print support, stability or another load case.')
    np.savez_compressed(args.output/'energy.npz',energy_Nmm=energy,volume_mm3=volume,peak_density_MPa=peak,low=low,pixel_mm=2)
    (args.output/'energy.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
