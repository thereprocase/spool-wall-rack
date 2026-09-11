"""Cached Rev G plane-stress evaluator, preserving the canonical F equations.

The mesh, finished layer membership, wall masks and load patches are reusable.
No stiffness is assigned to sparse infill. This is a search screen, not the
3D fracture or buckling acceptance model.
"""
from pathlib import Path
import hashlib
import json
import sys
import time
import numpy as np
import gmsh
from shapely import contains_xy, from_wkb
from shapely.geometry import LineString
from scipy.sparse.linalg import spsolve
from skfem import MeshTri, Basis, ElementVector, ElementTriP1, BilinearForm, asm
from skfem.helpers import ddot, sym_grad, trace

D = Path(__file__).resolve().parent
ROOT = D.parents[1]
sys.path.insert(0, str(ROOT / 'designs/rev-g'))
import layout
WORK = D / '.work'
WORK.mkdir(exist_ok=True)
E = 1000.
NU = .35
MU = E / (2 * (1 + NU))
LAM = E * NU / (1 - NU**2)


@BilinearForm
def elasticity(u, v, w):
    return w.th * (2 * MU * ddot(sym_grad(u), sym_grad(v))
                   + LAM * trace(sym_grad(u)) * trace(sym_grad(v)))


def source_hash():
    files = [Path(__file__), ROOT / 'designs/rev-g/layout.py',
             ROOT / 'analysis/rev-f/inputs/e13-layer-outlines.json',
             ROOT / 'analysis/e13/requirements.txt']
    h = hashlib.sha256()
    for path in files:
        h.update(path.read_text(encoding='utf-8').encode('utf-8'))
    return h.hexdigest()


def mesh_polygon(poly, h):
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal', 0)
        gmsh.option.setNumber('General.NumThreads', 1)
        gmsh.model.add('rev-g-screen')
        loops = []
        for ring in [poly.exterior, *poly.interiors]:
            pts = [gmsh.model.geo.addPoint(x, y, 0, h)
                   for x, y in list(ring.coords)[:-1]]
            lines = [gmsh.model.geo.addLine(a, b)
                     for a, b in zip(pts, pts[1:] + pts[:1])]
            loops.append(gmsh.model.geo.addCurveLoop(lines))
        gmsh.model.geo.addPlaneSurface(loops)
        gmsh.model.geo.synchronize()
        gmsh.option.setNumber('Mesh.MeshSizeMin', .25)
        gmsh.option.setNumber('Mesh.MeshSizeMax', h)
        gmsh.model.mesh.generate(2)
        tags, p, _ = gmsh.model.mesh.getNodes()
        p = np.array(p).reshape(-1, 3)[:, :2]
        kinds, _, cells = gmsh.model.mesh.getElements(2)
        t = np.array(cells[list(kinds).index(2)]).reshape(-1, 3)
        lookup = np.zeros(int(tags.max()) + 1, dtype=int)
        lookup[tags] = np.arange(len(tags))
        t = lookup[t]
    finally:
        gmsh.finalize()
    used, inv = np.unique(t, return_inverse=True)
    return p[used], inv.reshape(-1, 3)


class Screen:
    def __init__(self, h=2., window_scale=1., mesh_path=None):
        self.h = float(h)
        self.window_scale = float(window_scale)
        self.outline = layout.outline()
        self.poly = self.outline.difference(layout.windows({'window_scale': window_scale}))
        assert self.poly.geom_type == 'Polygon' and self.poly.is_valid
        geometry_hash = hashlib.sha256(self.poly.wkb + str(h).encode()).hexdigest()[:20]
        cache = WORK / f'mesh-{geometry_hash}.npz'
        if mesh_path is not None:
            with np.load(mesh_path, allow_pickle=False) as data:
                self.p, self.t = data['p'].copy(), data['t'].copy()
        elif cache.exists():
            with np.load(cache) as data:
                self.p, self.t = data['p'], data['t']
        else:
            self.p, self.t = mesh_polygon(self.poly, h)
            np.savez_compressed(cache, p=self.p, t=self.t)
        self.mesh_hash = hashlib.sha256(self.p.tobytes() + self.t.tobytes()).hexdigest()
        self.mesh = MeshTri(self.p.T, self.t.T)
        self.basis = Basis(self.mesh, ElementVector(ElementTriP1()))
        self.coords = self.basis.global_coordinates()
        self.z = (np.arange(120) + .5) * .2
        record = json.loads((ROOT / 'analysis/rev-f/inputs/e13-layer-outlines.json').read_text())
        expected = hashlib.sha256((ROOT / 'designs/closed-wall-e13/body-mounted.stl').read_bytes()).hexdigest()
        assert record['stl_sha256'] == expected
        outlines = [from_wkb(bytes.fromhex(s)) for s in record['wkb_hex']]
        params = {'window_scale': window_scale}
        self.layers = [p.difference(layout.windows_at_z(params, z))
                       for p, z in zip(outlines, self.z)]
        self.layer_hash = hashlib.sha256(b''.join(p.wkb for p in self.layers)).hexdigest()
        self.body = np.array([self.contains(p) for p in self.layers])
        self.envelope_volume = sum(p.area * .2 for p in self.layers)
        self._walls = {}
        self._saddles = {}
        self._prepare_loads()

    def contains(self, shape):
        return contains_xy(shape, self.coords[0], self.coords[1])

    def walls(self, n):
        n = int(n)
        if n not in self._walls:
            path = WORK / f'walls-{self.mesh_hash[:16]}-{self.layer_hash[:12]}-n{n}.npz'
            if path.exists():
                with np.load(path) as data:
                    masks = data['masks']
            else:
                width = .42 + (n - 1) * (.45 - .2 * (1 - np.pi / 4))
                masks = np.array([self.contains(p.difference(p.buffer(-width, quad_segs=12)))
                                  for p in self.layers])
                np.savez_compressed(path, masks=masks)
            self._walls[n] = masks
        return self._walls[n]

    def saddle(self, label, thickness):
        key = label, float(thickness)
        if thickness <= 0:
            return False
        if key not in self._saddles:
            y, length = (40, 50) if label == 'lower' else (164, 25)
            profile = layout.tunnel_collar_profile(y, thickness)
            bounds = []
            for z in self.z:
                section = profile.intersection(LineString([(0, z), (200, z)]))
                bounds.append((1., -1.) if section.is_empty else (section.bounds[0], section.bounds[2]))
            bounds = np.array(bounds)
            x, yy = self.coords
            self._saddles[key] = ((x[None] > 0) & (x[None] < length)
                                  & (yy[None] > bounds[:, 0, None, None])
                                  & (yy[None] < bounds[:, 1, None, None]))
        return self._saddles[key]

    def thickness(self, params):
        assert abs(params.get('window_scale', 1.) - self.window_scale) < 1e-10
        occupied = self.walls(params['walls']).copy()
        bands = layout.plate_bands(params)
        skins = (self.z < bands[0][1]) | (self.z > bands[-1][0])
        planes = ((self.z > bands[1][0]) & (self.z < bands[1][1])
                  | (self.z > bands[2][0]) & (self.z < bands[2][1]))
        occupied[skins] = self.body[skins]
        ribs = True if params.get('planes', 'full') == 'full' else self.contains(layout.rib_plane_region(self.outline, params))
        occupied[planes] |= self.body[planes] & ribs
        if not params.get('baseline', False):
            dense = self.contains(layout.dense_region(self.outline, params))
            occupied |= self.body & dense[None]
            for label in ['lower', 'upper']:
                occupied |= self.body & self.saddle(label, params.get(label + '_tunnel_collar_mm', 0))
        th = .2 * occupied.sum(axis=0)
        assert np.all(th > 0) and np.all(np.isfinite(th))
        return th

    def _prepare_loads(self):
        p, m = self.p, self.mesh
        edges = m.facets[:, m.boundary_facets()].T
        ec = p[edges].mean(axis=1)
        length = np.linalg.norm(p[edges[:, 1]] - p[edges[:, 0]], axis=1)
        S = np.hypot(100, 12)
        q = np.sqrt((90 + 12.4)**2 - S*S/4)
        cx, cy = 140 - 12*q/S, 6 + 100*q/S
        aa, bb = cx-90, 190-cx
        den = aa*(cy-12) + bb*cy
        H, Vr, Vf = 117.72*aa*bb/den, 117.72*bb*cy/den, 117.72*aa*(cy-12)/den
        self.loads = {}
        self.patches = {}
        for x, sign, label in [(90, -1, 'rear'), (190, 1, 'front')]:
            y, V = (0, Vr) if x == 90 else (12, Vf)
            angle = np.arctan2(ec[:, 1]-y, ec[:, 0]-x) - np.arctan2(-V, sign*H)
            delta = np.arctan2(np.sin(angle), np.cos(angle))
            mask = ((abs(np.hypot(ec[:, 0]-x, ec[:, 1]-y)-13) < .12)
                    & (abs(delta) < np.deg2rad(25)))
            es, wt = edges[mask], length[mask]
            assert len(es) > 0
            f = np.zeros(2*len(p))
            wt = wt/wt.sum()/2
            for j in range(2):
                for k, F in enumerate([sign*H, -V]):
                    np.add.at(f, 2*es[:, j]+k, wt*F)
            self.loads[label] = f
            self.patches[label] = np.unique(es)
        self.wall = np.where(abs(p[:, 0]) < 1e-6)[0]
        base = []
        for y in [164, 40]:
            head = self.wall[abs(p[self.wall, 1]-y) < 6.5]
            shank = self.wall[abs(p[self.wall, 1]-y) < 2.6]
            assert len(head) and len(shank)
            base.extend(2*head)
            base.extend(2*shank+1)
        self.base = np.array(base, dtype=int)

    def solve(self, params, load_case='full', field_path=None):
        started = time.perf_counter()
        th = self.thickness(params)
        K = asm(elasticity, self.basis, th=th).tocsr()
        f = self.loads['front'].copy()
        if load_case == 'full':
            f += self.loads['rear']
        else:
            assert load_case == 'outer_only'
        active = self.wall.copy()
        u = np.zeros(K.shape[0])
        diagonal = K.diagonal()
        for iteration in range(30):
            fixed = np.union1d(self.base, 2*active).astype(int)
            free = np.setdiff1d(np.arange(K.shape[0]), fixed)
            u[:] = 0
            u[free] = spsolve(K[free][:, free], f[free])
            reaction = K@u-f
            new = self.wall[(reaction[2*self.wall]-diagonal[2*self.wall]*u[2*self.wall]) > 1e-7]
            if np.array_equal(new, active):
                break
            active = new
        else:
            raise RuntimeError('Contact did not converge')
        residual = float(np.linalg.norm(reaction[free])/np.linalg.norm(f[free]))
        force = f.reshape(-1, 2).sum(axis=0)
        react = reaction.reshape(-1, 2).sum(axis=0)
        moment = float((self.p[:, 0]*f[1::2]-self.p[:, 1]*f[0::2]).sum())
        rmoment = float((self.p[:, 0]*reaction[1::2]-self.p[:, 1]*reaction[0::2]).sum())
        assert residual < 1e-6
        assert np.linalg.norm(force+react) < 1e-5 and abs(moment+rmoment) < 1e-3
        gradient = self.basis.interpolate(u).grad.mean(axis=-1)
        eps = (gradient+gradient.transpose(1, 0, 2))/2
        stress = 2*MU*eps+LAM*np.einsum('iie->e', eps)[None, None, :]*np.eye(2)[:, :, None]
        principal = np.linalg.eigvalsh(stress.transpose(2, 0, 1))[:, -1]
        vm = np.sqrt(stress[0, 0]**2-stress[0, 0]*stress[1, 1]+stress[1, 1]**2+3*stress[0, 1]**2)
        volume = (self.basis.dx*th).sum(axis=1)
        mass = (volume.sum()+(self.envelope_volume-volume.sum())*params.get('infill_percent', 5)/100)*1.24/1000
        movement = {name: -float(u.reshape(-1, 2)[nodes, 1].mean())
                    for name, nodes in self.patches.items()}
        row = {'parameters': params, 'mesh_h_mm': self.h, 'mesh_hash': self.mesh_hash,
               'load_case': load_case, 'nodes': len(self.p), 'triangles': len(self.t),
               'front_movement_mm_at_E1000': movement['front'],
               'rear_movement_mm_at_E1000': movement['rear'],
               'raw_peak_tensile_MPa': float(principal.max()), 'raw_peak_VM_MPa': float(vm.max()),
               'conservative_40p5MPa_strength_ratio': float(40.5/principal.max()),
               'load_compliance_Nmm_at_E1000': float(f@u),
               'structural_quadrature_volume_mm3': float(volume.sum()),
               'nominal_mass_proxy_g_at_1p24': float(mass),
               'body_layer_volume_mm3': self.envelope_volume,
               'relative_free_residual': residual,
               'relative_force_balance_error': float(np.linalg.norm(force+react)/np.linalg.norm(force)),
               'relative_moment_balance_error': abs(moment+rmoment)/abs(moment),
               'contact_iterations': iteration+1,
               'elapsed_seconds': time.perf_counter()-started}
        if field_path is not None:
            np.savez_compressed(field_path, p=self.p, t=self.t, u=u.reshape(-1, 2),
                                stress=stress, principal=principal, vm=vm, volume=volume, thickness=th.mean(axis=1))
        return row
