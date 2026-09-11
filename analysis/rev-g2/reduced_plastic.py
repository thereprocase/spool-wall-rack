"""Provisional Rev-G reduced plane-stress recheck from actual sliced plastic.

The 2D mesh is a fresh projection of the unchanged G sliced-material footprint.
Exact triangle/layer intersections supply its integrated material thickness;
the former hand-cut shell/core and density model are not reused.  This is a
ranking diagnostic only; it is not a 3D fracture or print qualification.
"""
from __future__ import annotations
import argparse, hashlib, json, sys, time
from pathlib import Path
import gmsh
import numpy as np
import shapely
from shapely import union_all
from scipy.sparse.linalg import splu
from skfem import MeshTri, Basis, ElementVector, ElementTriP1, BilinearForm, asm
from skfem.helpers import ddot, sym_grad, trace

D = Path(__file__).resolve().parent
ROOT = D.parents[1]
sys.path.insert(0, str(D))
from plastic_shape import PlasticShape
from solve_plastic import interface_loads

E = 1000.0
NU = .35
MU = E/(2*(1+NU))
LAM = E*NU/(1-NU**2)

@BilinearForm
def elasticity(u, v, w):
    return w.th * (2*MU*ddot(sym_grad(u), sym_grad(v)) + LAM*trace(sym_grad(u))*trace(sym_grad(v)))

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1<<20), b''): h.update(b)
    return h.hexdigest()

def make_mesh(poly, h):
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal', 0)
        gmsh.option.setNumber('General.NumThreads', 1)
        gmsh.model.add('rev-g2-reduced')
        loops=[]
        for ring in [poly.exterior, *poly.interiors]:
            pts=[gmsh.model.geo.addPoint(float(x),float(y),0,float(h)) for x,y in list(ring.coords)[:-1]]
            lines=[gmsh.model.geo.addLine(a,b) for a,b in zip(pts,pts[1:]+pts[:1])]
            loops.append(gmsh.model.geo.addCurveLoop(lines))
        gmsh.model.geo.addPlaneSurface(loops)
        gmsh.model.geo.synchronize()
        gmsh.option.setNumber('Mesh.MeshSizeMin', min(.25, h))
        gmsh.option.setNumber('Mesh.MeshSizeMax', h)
        gmsh.model.mesh.generate(2)
        tags, coords, _ = gmsh.model.mesh.getNodes()
        p=np.asarray(coords).reshape(-1,3)[:,:2]
        kinds,_,cells=gmsh.model.mesh.getElements(2)
        t=np.asarray(cells[list(kinds).index(2)]).reshape(-1,3)
        lookup=np.zeros(int(tags.max())+1,dtype=int); lookup[tags]=np.arange(len(tags)); t=lookup[t]
    finally: gmsh.finalize()
    used, inv=np.unique(t,return_inverse=True)
    p=p[used]; t=inv.reshape(-1,3)
    q = p[t]
    cross=(q[:,1,0]-q[:,0,0])*(q[:,2,1]-q[:,0,1])-(q[:,1,1]-q[:,0,1])*(q[:,2,0]-q[:,0,0])
    longest_squared = np.max([np.sum((q[:,i]-q[:,j])**2, axis=1) for i,j in [(0,1),(1,2),(2,0)]], axis=0)
    normalized = np.abs(cross)/np.maximum(longest_squared, np.finfo(float).tiny)
    bad = normalized < 1e-12
    audit = {'input_triangles': len(t), 'removed_numerically_degenerate_triangles': int(bad.sum()),
             'normalized_twice_area_floor': 1e-12,
             'removed_absolute_area_mm2': float(np.abs(cross[bad]).sum()/2),
             'removed_material_volume_upper_bound_at_24_mm_mm3': float(np.abs(cross[bad]).sum()/2*24)}
    assert audit['removed_material_volume_upper_bound_at_24_mm_mm3'] < 1e-8, 'Non-negligible material removal; remesh'
    t=t[~bad]
    used, inv=np.unique(t,return_inverse=True)
    return p[used], inv.reshape(-1,3), audit

class Reduced:
    def __init__(self, shape, h):
        self.shape=shape
        self.projection=union_all([row[2] for row in shape.layers])
        assert self.projection.is_valid and self.projection.geom_type == 'Polygon'
        self.p,self.t,self.mesh_audit=make_mesh(self.projection,h)
        self.mesh=MeshTri(self.p.T,self.t.T)
        self.basis=Basis(self.mesh,ElementVector(ElementTriP1()))
        self.coords=self.basis.global_coordinates()
        qxy=self.coords.transpose(1,2,0).reshape(-1,2)
        self.sampled_th=shape.equivalent_thickness(qxy).reshape(self.coords.shape[1:])
        assert np.all(np.isfinite(self.sampled_th)) and np.all(self.sampled_th>=0)
        self.zero_thickness_quadrature=int(np.count_nonzero(self.sampled_th==0))
        self.area = self.basis.dx.sum(axis=1)
        key = hashlib.sha256(b'integrated-triangle-volume-v1'+self.p.tobytes()+self.t.tobytes())
        for z0,z1,raw,_simple in shape.layers:
            key.update(np.array([z0,z1]).tobytes()); key.update(raw.wkb)
        signature = key.hexdigest()
        cache = D/'.work/integrated-thickness'/f'{signature}.npz'
        start = time.perf_counter()
        cached = cache.exists()
        if cached:
            with np.load(cache) as data:
                assert data['signature'].item() == signature
                self.material_volume = data['volume']
        else:
            print('integrate exact sliced material over', len(self.t), 'triangles', flush=True)
            self.material_volume = shape.integrated_volume(shapely.polygons(self.p[self.t]), workers=4)
            cache.parent.mkdir(parents=True,exist_ok=True)
            np.savez_compressed(cache, signature=signature, volume=self.material_volume)
        assert self.material_volume.shape == (len(self.t),)
        empty = self.material_volume == 0
        if empty.any():
            # Raw projection boundaries can leave roundoff-scale triangles.
            # Remove only elements with exactly zero integrated plastic and
            # negligible total area. Retain the original integration cache.
            empty_area = float(self.area[empty].sum())
            assert empty_area < 1e-8, f'Non-negligible empty projection elements: {empty_area}; remesh'
            self.mesh_audit.update(zero_material_roundoff_triangles=int(empty.sum()),
                                   zero_material_roundoff_area_mm2=empty_area,
                                   removed_integrated_plastic_volume_mm3=0.0)
            used, inverse = np.unique(self.t[~empty], return_inverse=True)
            self.p = self.p[used]; self.t = inverse.reshape(-1, 3)
            self.mesh = MeshTri(self.p.T, self.t.T)
            self.basis = Basis(self.mesh, ElementVector(ElementTriP1()))
            self.coords = self.basis.global_coordinates()
            self.area = self.basis.dx.sum(axis=1)
            self.sampled_th = self.sampled_th[~empty]
            self.zero_thickness_quadrature = int(np.count_nonzero(self.sampled_th == 0))
            self.material_volume = self.material_volume[~empty]
        assert np.all(np.isfinite(self.material_volume)) and np.all(self.material_volume > 0)
        # A P1 triangle has constant strain. The exact area-integrated material
        # thickness therefore gives its stiffness without quadrature sampling.
        mean_thickness = self.material_volume/self.area
        self.th_for_stiffness = np.broadcast_to(mean_thickness[:,None], self.basis.dx.shape)
        self.integration = {'method': 'Exact layer-polygon / element intersections; constant P1 strain.',
                            'signature': signature, 'cache_hit': cached,
                            'elapsed_seconds': time.perf_counter()-start}
        assert abs(self.material_volume.sum()/shape.volume()-1) < 1e-7
        self._loads()

    def _loads(self):
        p,m=self.p,self.mesh
        edges=m.facets[:,m.boundary_facets()].T
        ec=p[edges].mean(axis=1); length=np.linalg.norm(p[edges[:,1]]-p[edges[:,0]],axis=1)
        self.loads={}; self.patches={}; self.patch_geometry={}; self.patch_weights={}
        forces = interface_loads(117.72)
        for x,y,label in [(90.,0.,'rear'),(190.,12.,'front')]:
            force = forces[label+'_seat'][:2]
            angle=np.arctan2(ec[:,1]-y,ec[:,0]-x)-np.arctan2(force[1],force[0]); delta=np.arctan2(np.sin(angle),np.cos(angle))
            mask=(abs(np.hypot(ec[:,0]-x,ec[:,1]-y)-13)<.17)&(abs(delta)<np.deg2rad(25))
            assert np.any(mask), f'load patch missing: {label}'
            es,wt=edges[mask],length[mask]; f=np.zeros(2*len(p)); wt=wt/wt.sum()/2
            for j in range(2):
                for k,F in enumerate(force): np.add.at(f,2*es[:,j]+k,wt*F)
            self.loads[label]=f; self.patches[label]=np.unique(es)
            self.patch_weights[label] = np.linalg.norm(f.reshape(-1,2),axis=1)/np.linalg.norm(force)
            self.patch_geometry[label]={'center_XY_mm':[x,y],'force_XY_N':force.tolist(),'radius_mm':13.0,'radius_tolerance_mm':.17,'arc_degrees':50.0,'edge_count':int(mask.sum()),'total_edge_length_mm':float(length[mask].sum()), 'distribution': 'Uniform per projected edge length; 3D distributes over actual face area.'}
        xmin=float(self.p[:,0].min())
        tangent = (p[edges[:,1]]-p[edges[:,0]])/length[:,None]
        wall_edges = (ec[:,0] < xmin+.05) & (np.abs(tangent[:,1]) > .9)
        self.wall=np.unique(edges[wall_edges]); assert len(self.wall)>0
        self.wall_plane_x = float(p[self.wall,0].min())
        self.gap0 = p[self.wall,0]-self.wall_plane_x
        base=[]
        for y in (164,40):
            head=self.wall[abs(self.p[self.wall,1]-y)<6.5]; shank=self.wall[abs(self.p[self.wall,1]-y)<2.6]
            assert len(head) and len(shank), f'fixing land missing at Y={y}'
            base.extend(2*head); base.extend(2*shank+1)
        self.base=np.array(base,dtype=int)
        assert self.projection.bounds[0] <= xmin+.01 and all(np.isfinite(self.projection.bounds))

    def solve(self):
        started = time.perf_counter()
        K = asm(elasticity, self.basis, th=self.th_for_stiffness).tocsr()
        f = self.loads['front']+self.loads['rear']
        active = self.wall[self.gap0 < 1e-9]
        u = np.zeros(K.shape[0])
        diagonal = K.diagonal()
        iterations = []
        for iteration in range(30):
            fixed = np.union1d(self.base, 2*active).astype(int)
            free = np.setdiff1d(np.arange(K.shape[0]), fixed)
            u[:] = 0.
            u[2*active] = -self.gap0[np.searchsorted(self.wall, active)]
            A = K[free][:, free]
            rhs = f[free]-K[free][:, fixed]@u[fixed]
            factor = splu(A.tocsc(), permc_spec='MMD_AT_PLUS_A', options={'Equil': True})
            sol = factor.solve(rhs)
            for _ in range(3):
                sol += factor.solve(rhs-A@sol)
            u[free] = sol
            reaction = K@u-f
            gap = u[2*self.wall]+self.gap0
            new = self.wall[(reaction[2*self.wall]-diagonal[2*self.wall]*gap) > 1e-7]
            iterations.append({'step': iteration, 'active_nodes': len(active),
                               'next_active_nodes': len(new), 'minimum_gap_mm': float(gap.min())})
            if np.array_equal(new, active):
                break
            active = new
        else:
            raise RuntimeError('contact did not converge')
        residual = float(np.linalg.norm(reaction[free])/max(np.linalg.norm(f[free]), 1e-30))
        applied = f.reshape(-1, 2)
        reacted = reaction.reshape(-1, 2)
        force, react = applied.sum(axis=0), reacted.sum(axis=0)
        moment = float((self.p[:,0]*applied[:,1]-self.p[:,1]*applied[:,0]).sum())
        rmoment = float((self.p[:,0]*reacted[:,1]-self.p[:,1]*reacted[:,0]).sum())
        force_error = float(np.linalg.norm(force+react)/np.linalg.norm(force))
        moment_error = float(abs(moment+rmoment)/abs(moment))
        assert max(residual, force_error, moment_error) < 1e-6
        assert gap.min() >= -1e-8
        assert not len(active) or reaction[2*active].min() >= -1e-7
        grad = self.basis.interpolate(u).grad.mean(axis=-1)
        eps = (grad+grad.transpose(1,0,2))/2
        stress = 2*MU*eps+LAM*np.einsum('iie->e',eps)[None,None,:]*np.eye(2)[:,:,None]
        principal = np.linalg.eigvalsh(stress.transpose(2,0,1))[:,-1]
        U = u.reshape(-1,2)
        assert np.isfinite(U).all() and np.isfinite(stress).all()
        peak = int(np.argmax(principal))
        patches = {}
        for label, nodes in self.patches.items():
            average = self.patch_weights[label]@U
            patches[label] = {**self.patch_geometry[label],
                              'load_weighted_mean_displacement_XY_mm': average.tolist(),
                              'maximum_resultant_displacement_mm': float(np.linalg.norm(U[nodes],axis=1).max())}
        volume, exact = float(self.material_volume.sum()), float(self.shape.volume())
        rel = abs(volume/exact-1)
        assert rel < 1e-7
        self.fields = {'p': self.p, 't': self.t, 'u': U, 'stress': stress,
                       'element_material_volume': self.material_volume,
                       'element_mean_thickness': self.material_volume/self.area,
                       'sampled_quadrature_thickness': self.sampled_th,
                       'area': self.area, 'applied_force': applied, 'reaction': reacted,
                       'wall_nodes': self.wall, 'active_wall': active, 'initial_wall_gap': self.gap0}
        return {
            'status': 'DIAGNOSTIC_2D_RANKING_ONLY', 'E_planning_MPa': E, 'nu': NU,
            'nodes': len(self.p), 'triangles': len(self.t),
            'projection_bounds_XY_mm': list(self.projection.bounds), 'mesh_audit': self.mesh_audit,
            'projection_mesh_hash': hashlib.sha256(self.p.tobytes()+self.t.tobytes()).hexdigest(),
            'integrated_structural_volume_mm3': volume, 'plastic_shape_union_volume_mm3': exact,
            'relative_integrated_volume_difference': rel, 'volume_integration': self.integration,
            'sampled_quadrature_volume_mm3': float((self.basis.dx*self.sampled_th).sum()),
            'zero_sampled_thickness_quadrature_points': self.zero_thickness_quadrature,
            'front_movement_mm': -patches['front']['load_weighted_mean_displacement_XY_mm'][1],
            'rear_movement_mm': -patches['rear']['load_weighted_mean_displacement_XY_mm'][1],
            'maximum_resultant_displacement_mm': float(np.linalg.norm(U,axis=1).max()),
            'raw_peak_tensile_MPa': float(principal[peak]),
            'raw_peak_centroid_XY_mm': self.p[self.t[peak]].mean(axis=0).tolist(),
            'raw_peak_element_area_mm2': float(self.area[peak]),
            'relative_free_residual': residual, 'relative_force_balance_error': force_error,
            'relative_moment_balance_error': moment_error, 'contact_iterations': iterations,
            'active_wall_nodes': len(active), 'wall_minimum_gap_mm': float(gap.min()),
            'active_wall_minimum_reaction_N': float(reaction[2*active].min()) if len(active) else None,
            'wall_plane_x_mm': self.wall_plane_x, 'maximum_initial_wall_gap_mm': float(self.gap0.max()),
            'applied_force_N': force.tolist(), 'reaction_N': react.tolist(),
            'applied_moment_Nmm': moment, 'reaction_moment_Nmm': rmoment, 'patches': patches,
            'wall_model': 'Projected 2D fixings at the wall boundary; initial X gaps retained. The 3D washer plane at X=3.6 and through-width restraint are collapsed in this model.',
            'material_policy': 'Exact triangle/layer intersections of credited nominal footprints. Thick bridges excluded. P1 strain is constant in each element; no artificial stiffness is added at empty quadrature points.',
            'scope': 'Isotropic E=1000 MPa plane-stress ranking diagnostic; displacement is assumed uniform through Z. 3D fracture, buckling, physical process and lifetime qualification remain separate.',
            'solve_elapsed_seconds': time.perf_counter()-started,
        }


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--shape',type=Path,default=ROOT/'analysis/rev-g2/g-recheck/2w-5layers/validated-shape'); ap.add_argument('--output',type=Path,default=ROOT/'analysis/rev-g2/reduced-plastic/2w-5layers.json'); ap.add_argument('--h',type=float,default=2.0); args=ap.parse_args()
    args.shape=args.shape.resolve(); args.output=args.output.resolve()
    started=time.perf_counter()
    shape=PlasticShape.load(args.shape)
    reduced=Reduced(shape,args.h); solve=reduced.solve(); solve.update({'shape_dir':str(args.shape.relative_to(ROOT)).replace('\\','/'),'shape_verification_sha256':digest(args.shape/'shape-verification.json'),'mesh_h_mm':args.h})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    npz=args.output.with_suffix('.npz')
    np.savez_compressed(npz,**reduced.fields)
    solve.update({'field_sha256':digest(npz),'total_elapsed_seconds':time.perf_counter()-started})
    args.output.write_text(json.dumps(solve,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(solve,indent=2),flush=True)

if __name__=='__main__': main()
