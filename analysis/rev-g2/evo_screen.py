"""G-anchored helper-allocation screen; conditional ranking, not print physics.

The baseline uses exact integrated raw sliced material. Helper changes use
an explicitly approximate, baseline-normalized occupancy response. Every
candidate needs a new Orca slice and 3D check before promotion to a prototype.
"""
from pathlib import Path
import argparse, hashlib, json, sys, time
import numpy as np
import shapely
from shapely.geometry import LineString
from scipy.sparse.linalg import splu
from skfem import MeshTri, Basis, ElementVector, ElementTriP1, BilinearForm, asm
from skfem.helpers import ddot, sym_grad, trace

D=Path(__file__).resolve().parent
ROOT=D.parents[1]
sys.path.insert(0,str(ROOT/'designs/rev-g'))
import layout

GENES=['bottom_band','diagonal_band','seat_band','front_seat_band',
       'lower_tunnel_collar_mm','upper_tunnel_collar_mm']
BASE=json.loads((ROOT/'designs/rev-g/selected-layout.json').read_text())
BASE.update(walls=2,infill_percent=0,name='g-2w-5skins-screen-reference')
E=1000.;NU=.35;MU=E/(2*(1+NU));LAM=E*NU/(1-NU**2)


@BilinearForm
def elasticity(u,v,w):
    return w.th*(2*MU*ddot(sym_grad(u),sym_grad(v))+LAM*trace(sym_grad(u))*trace(sym_grad(v)))


def source_signature():
    paths=[Path(__file__),ROOT/'designs/rev-g/layout.py',ROOT/'designs/rev-g/selected-layout.json',
           D/'plastic_shape.py',ROOT/'designs/rev-g2/g-recheck/2w-5layers/slice-evidence.zip',
           D/'reduced-plastic/2w-5layers-exact-h2.npz',
           ROOT/'analysis/rev-f/inputs/e13-layer-outlines.json',
           D/'g-results/reference-tight/audit.json']
    # Text dependencies may live in either Windows or WSL checkouts. Hash
    # their normalized contents; binary mesh/slice inputs retain exact bytes.
    return hashlib.sha256(b''.join(p.read_text(encoding='utf-8').encode() if p.suffix in ['.py','.json'] else p.read_bytes() for p in paths)).hexdigest()


class Screen:
    def __init__(self,cache):
        start=time.perf_counter();self.cache=Path(cache);self.cache.mkdir(parents=True,exist_ok=True)
        self.signature=source_signature()
        with np.load(D/'reduced-plastic/2w-5layers-exact-h2.npz') as d:
            self.p,self.t,self.volume,self.area=[d[k].copy() for k in ['p','t','element_material_volume','area']]
            self.reference_u=d['u'].ravel().copy();self.f=d['applied_force'].ravel().copy()
            self.wall=d['wall_nodes'].copy();self.gap0=d['initial_wall_gap'].copy();self.reference_active=d['active_wall'].copy()
        self.mesh=MeshTri(self.p.T,self.t.T);self.basis=Basis(self.mesh,ElementVector(ElementTriP1()))
        self.xy=self.basis.global_coordinates().transpose(1,2,0).reshape(-1,2)
        self.base=np.unique(np.concatenate([np.r_[2*self.wall[abs(self.p[self.wall,1]-y)<6.5],
                           2*self.wall[abs(self.p[self.wall,1]-y)<2.6]+1] for y in [40.,164.]]))
        self.z=(np.arange(120)+.5)*.2
        self.outline=layout.outline();self.centers=self.p[self.t].mean(axis=1)
        self.hotspot=np.linalg.norm(self.centers-[107.6423,-3.5577],axis=1)<8.
        self.reference_3d=json.loads((D/'g-results/reference-tight/audit.json').read_text())
        self._prepare_occupancy()
        self.ideal_reference=self.ideal_thickness(BASE)
        self.unresolved=self.ideal_reference<=1e-12
        self.unresolved_volume_fraction=float(self.volume[self.unresolved].sum()/self.volume.sum())
        # Exact baseline material is retained even where its footprint extends
        # outside the nominal CAD. Do not invent a response in those slivers.
        assert self.unresolved_volume_fraction<.005,self.unresolved_volume_fraction
        self.setup_seconds=time.perf_counter()-start

    def _prepare_occupancy(self):
        path=self.cache/'occupancy.npz'
        if path.exists():
            with np.load(path) as d:
                assert d['signature'].item()==self.signature,'Use a new cache for changed source'
                self.body,self.protected,self.bridge=[d[k].copy() for k in ['body','protected','bridge']]
            return
        rows=json.loads((ROOT/'analysis/rev-f/inputs/e13-layer-outlines.json').read_text())
        sections=[shapely.from_wkb(bytes.fromhex(x)).difference(layout.windows_at_z(BASE,z))
                  for x,z in zip(rows['wkb_hex'],self.z)]
        width=.42+.45-.2*(1-np.pi/4)
        self.body=np.array([shapely.contains_xy(p,self.xy[:,0],self.xy[:,1]) for p in sections])
        self.protected=np.array([shapely.contains_xy(p.difference(p.buffer(-width,quad_segs=12)),self.xy[:,0],self.xy[:,1]) for p in sections])
        bands=layout.plate_bands(BASE)
        for lo,hi in bands:self.protected[(self.z>lo)&(self.z<hi)]=self.body[(self.z>lo)&(self.z<hi)]
        # Never give the known reference sacrificial bridge footprint helper
        # stiffness in the occupancy-response surrogate.
        from plastic_shape import read_paths,layer_shapes
        paths,_=read_paths(ROOT/'designs/rev-g2/g-recheck/2w-5layers/.work/audit-2w')
        paths=dict(paths);paths['structural']=~paths['structural']
        layers=layer_shapes(paths,simplify_mm=0.)
        self.bridge=np.zeros_like(self.body)
        for k,z in enumerate(self.z):
            shapes=[r[2] for r in layers if r[0]<z<r[1]]
            if shapes:self.bridge[k]=shapely.contains_xy(shapely.union_all(shapes),self.xy[:,0],self.xy[:,1])
        np.savez_compressed(path,signature=self.signature,body=self.body,protected=self.protected,bridge=self.bridge)

    def ideal_thickness(self,params):
        dense=shapely.contains_xy(layout.dense_region(self.outline,params),self.xy[:,0],self.xy[:,1])
        occupied=self.protected.copy()
        helper=np.broadcast_to(dense,self.body.shape).copy()
        for label,y,length in [('lower',40.,50.),('upper',164.,25.)]:
            profile=layout.tunnel_collar_profile(y,params[label+'_tunnel_collar_mm'])
            for k,z in enumerate(self.z):
                section=profile.intersection(LineString([(0,z),(200,z)]))
                if not section.is_empty:
                    lo,_,hi,_=section.bounds
                    helper[k]|=(self.xy[:,0]>0)&(self.xy[:,0]<length)&(self.xy[:,1]>lo)&(self.xy[:,1]<hi)
        occupied|=helper&self.body&~self.bridge
        return (.2*occupied.sum(axis=0)).reshape(len(self.t),-1).mean(axis=1)

    def candidate_volume(self,params):
        ideal=self.ideal_thickness(params)
        factor=np.ones(len(self.t));resolved=~self.unresolved
        factor[resolved]=ideal[resolved]/self.ideal_reference[resolved]
        assert np.all(np.isfinite(factor)) and np.all(factor>0),'Candidate lost projected material connectivity'
        # This is a calibrated occupancy surrogate, not a new raw-slice cache.
        return self.volume*factor

    def solve(self,volume,initial=None,active=None,max_seconds=30.):
        started=time.perf_counter()
        K=asm(elasticity,self.basis,th=np.broadcast_to((volume/self.area)[:,None],self.basis.dx.shape)).tocsr()
        diagonal=K.diagonal();u=self.reference_u.copy() if initial is None else initial.copy()
        active=self.reference_active.copy() if active is None else active.copy()
        history=[];status='FAIL_CONTACT_ITERATIONS'
        for step in range(30):
            applied_active=active.copy();fixed=np.union1d(self.base,2*active).astype(int)
            free=np.setdiff1d(np.arange(len(u)),fixed)
            u[fixed]=0.;u[2*active]=-self.gap0[np.searchsorted(self.wall,active)]
            rhs=self.f[free]-K[free][:,fixed]@u[fixed]
            A=K[free][:,free]
            r=K@u-self.f
            relative=float(np.linalg.norm(r[free])/max(np.linalg.norm(self.f),1e-30))
            if relative>5e-7:
                factor=splu(A.tocsc(),permc_spec='MMD_AT_PLUS_A',options={'Equil':True})
                x=factor.solve(rhs)
                for _ in range(3):x+=factor.solve(rhs-A@x)
                u[free]=x;r=K@u-self.f
                relative=float(np.linalg.norm(r[free])/np.linalg.norm(self.f))
            gaps=u[2*self.wall]+self.gap0
            next_active=self.wall[r[2*self.wall]-diagonal[2*self.wall]*gaps>1e-7]
            history.append({'step':step,'active_nodes':len(active),'next_active_nodes':len(next_active),'relative_free_residual':relative})
            if relative>=1e-6:status='FAIL_LINEAR_EQUILIBRIUM';break
            if np.array_equal(active,next_active):
                status='PASS_REDUCED_CONTACT' if gaps.min()>=-1e-8 and r[2*active].min(initial=0)>=-1e-7 else 'FAIL_CONTACT_INEQUALITIES'
                break
            if time.perf_counter()-started>max_seconds:status='FAIL_TIME_BUDGET';break
            active=next_active
        gradient=self.basis.interpolate(u).grad.mean(axis=-1)
        strain=(gradient+gradient.transpose(1,0,2))/2
        stress=2*MU*strain+LAM*np.einsum('iie->e',strain)[None,None,:]*np.eye(2)[:,:,None]
        principal=np.linalg.eigvalsh(stress.transpose(2,0,1))[:,-1]
        assert np.isfinite(u).all() and np.isfinite(stress).all()
        constrained=np.zeros_like(r);constrained[fixed]=r[fixed]
        balance=(self.f+constrained).reshape(-1,2)
        force_error=float(np.linalg.norm(balance.sum(axis=0))/117.72)
        moment_error=float(abs((self.p[:,0]*balance[:,1]-self.p[:,1]*balance[:,0]).sum())/15236.685840586606)
        if max(force_error,moment_error)>=1e-6:status='FAIL_BALANCE'
        result={'status':status,'nominal_material_proxy_mm3':float(volume.sum()),'compliance_Nmm':float(self.f@u),
                'maximum_movement_mm':float(np.linalg.norm(u.reshape(-1,2),axis=1).max()),
                'raw_peak_tensile_MPa':float(principal.max()),'inner_seat_raw_peak_MPa':float(principal[self.hotspot].max()),
                'relative_force_error':force_error,'relative_moment_error':moment_error,
                'minimum_gap_mm':float(gaps.min()),'minimum_active_reaction_N':float(r[2*applied_active].min(initial=0)),
                'history':history,'elapsed_seconds':time.perf_counter()-started}
        fields={'u':u.reshape(-1,2),'stress':stress,'principal':principal,'volume':volume,
                'reaction':r.reshape(-1,2),'active_wall':applied_active,'wall_gaps':gaps}
        return result,fields

    def evaluate(self,params,output,max_seconds=30.):
        start=time.perf_counter();output=Path(output);output.mkdir(parents=True,exist_ok=False)
        volume=self.candidate_volume(params);result,fields=self.solve(volume,max_seconds=max_seconds)
        result.update(parameters=params,screen_signature=self.signature,
                      unchanged_baseline_volume_fraction=self.unresolved_volume_fraction,
                      interpretation='2D G-anchored helper-occupancy ranking proxy. Candidate volume is not an actual slice or spent plastic. No 3D strength or print qualification.')
        np.savez_compressed(output/'fields.npz',**fields)
        result['total_evaluation_seconds']=time.perf_counter()-start
        (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        return result


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    assert not args.output.exists();args.output.mkdir(parents=True)
    model=Screen(args.output/'cache')
    results=[]
    for name,changes in [('baseline',{}),('upper_trim',{'upper_tunnel_collar_mm':BASE['upper_tunnel_collar_mm']*.9}),
                         ('inner_seat_gain',{'seat_band':BASE['seat_band']*1.1})]:
        row=model.evaluate({**BASE,**changes},args.output/name)
        results.append(row)
        print(json.dumps({'case':name,'setup_seconds':model.setup_seconds,**{k:v for k,v in row.items() if k not in ['parameters','history']}},indent=2),flush=True)
    reference=json.loads((D/'reduced-plastic/2w-5layers-exact-h2.json').read_text())
    assert results[0]['status']=='PASS_REDUCED_CONTACT'
    assert abs(results[0]['maximum_movement_mm']/reference['maximum_resultant_displacement_mm']-1)<1e-6
    assert abs(results[0]['raw_peak_tensile_MPa']/reference['raw_peak_tensile_MPa']-1)<1e-6
    (args.output/'benchmark.json').write_text(json.dumps({'status':'PASS_BASELINE_REPLAY','setup_seconds':model.setup_seconds,'results':results},indent=2)+'\n')
