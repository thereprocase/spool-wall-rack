"""Bounded, matrix-free GPU Q1 hexahedral elasticity, N/mm/MPa.

Only full material cells exist. No density floor or ersatz stiffness is used.
Eight-point integration; every finite stress sample is retained. This initial
Jacobi-CG adapter has no multigrid and is not qualified for whole-G scale.
"""
from itertools import product
import time

import numpy as np
import warp as wp
from warp.optim.linear import LinearOperator, cg

CORNERS = np.array([[0,0,0], [1,0,0], [1,1,0], [0,1,0],
                    [0,0,1], [1,0,1], [1,1,1], [0,1,1]])


def element(spacing, E=1000., nu=.35):
    """Integrate the rectangular Q1 element explicitly at 2x2x2 Gauss points."""
    spacing = np.asarray(spacing, dtype=float)
    assert np.all(spacing > 0) and E > 0 and -1 < nu < .5
    mu, lam = E/(2*(1+nu)), E*nu/((1+nu)*(1-2*nu))
    C = np.zeros((6,6))
    C[:3,:3] = lam
    C[np.arange(3),np.arange(3)] += 2*mu
    C[3:,3:] = np.eye(3)*mu
    signs = 2*CORNERS-1
    Bs, locations = [], []
    for q in product([-1/np.sqrt(3), 1/np.sqrt(3)], repeat=3):
        grad = np.empty((8,3))
        for axis in range(3):
            others = [a for a in range(3) if a != axis]
            grad[:,axis] = signs[:,axis]*np.prod(1+signs[:,others]*np.array(q)[others], axis=1)/(4*spacing[axis])
        B = np.zeros((6,24))
        for a,(dx,dy,dz) in enumerate(grad):
            B[:,3*a:3*a+3] = [[dx,0,0],[0,dy,0],[0,0,dz],
                              [dy,dx,0],[0,dz,dy],[dz,0,dx]]
        Bs.append(B)
        locations.append((np.array(q)+1)*spacing/2)
    Bs = np.asarray(Bs)
    K = np.einsum('qai,ab,qbj->ij', Bs, C, Bs)*np.prod(spacing)/8
    return K, Bs, C, np.asarray(locations)


def mesh_from_cells(cells, spacing, origin=(0.,0.,0.)):
    """Build face-connected material, splitting edge/corner-only nodal ties.

At each lattice vertex, cell incidences share a node only if they connect via
faces incident to that vertex. A diagonal touch cannot create a bonded tie.
"""
    cells = np.asarray(cells, dtype=np.int32).reshape(-1,3)
    assert len(cells) and len(np.unique(cells,axis=0)) == len(cells)
    vertex, inverse = np.unique((cells[:,None,:]+CORNERS).reshape(-1,3), axis=0, return_inverse=True)
    order = np.argsort(inverse, kind='stable')
    starts = np.r_[0, np.flatnonzero(np.diff(inverse[order]))+1, len(order)]
    ids = np.empty(8*len(cells), dtype=np.int32)
    points = []
    split_vertices = 0
    for begin,end in zip(starts[:-1],starts[1:]):
        incident = order[begin:end]
        remaining = set(int(v) for v in incident)
        groups = 0
        while remaining:
            seed = remaining.pop()
            group, queue = [seed], [seed]
            while queue:
                current = queue.pop()
                linked = [j for j in remaining if np.abs(cells[j//8]-cells[current//8]).sum() == 1]
                for j in linked:
                    remaining.remove(j)
                    group.append(j)
                    queue.append(j)
            ids[group] = len(points)
            points.append(vertex[inverse[seed]])
            groups += 1
        split_vertices += groups > 1
    return (np.asarray(points)*np.asarray(spacing)+np.asarray(origin),
            ids.reshape(-1,8), {"split_edge_corner_vertices": split_vertices})


@wp.kernel
def multiply(conn: wp.array2d[int], offsets: wp.array[int], incidence: wp.array[int],
             ke: wp.array2d[wp.float64], fixed: wp.array[int],
             x: wp.array[wp.float64], y: wp.array[wp.float64], z: wp.array[wp.float64],
             alpha: wp.float64, beta: wp.float64):
    i = wp.tid()
    value = wp.float64(0.)
    if fixed[i] != 0:
        value = x[i]
    else:
        for pos in range(offsets[i], offsets[i+1]):
            local = incidence[pos]
            e, row = local//24, local%24
            for col in range(24):
                j = conn[e,col]
                if fixed[j] == 0:
                    value += ke[row,col]*x[j]
    result = alpha*value
    if beta != wp.float64(0.):
        result += beta*y[i]
    z[i] = result


@wp.kernel
def diagonal_multiply(inv: wp.array[wp.float64], x: wp.array[wp.float64],
                      y: wp.array[wp.float64], z: wp.array[wp.float64],
                      alpha: wp.float64, beta: wp.float64):
    i = wp.tid()
    result = alpha*inv[i]*x[i]
    if beta != wp.float64(0.):
        result += beta*y[i]
    z[i] = result


@wp.kernel
def recover(conn: wp.array2d[int], cb: wp.array3d[wp.float64],
            u: wp.array[wp.float64], stress: wp.array3d[wp.float64]):
    e,q,c = wp.tid()
    value = wp.float64(0.)
    for j in range(24):
        value += cb[q,c,j]*u[conn[e,j]]
    stress[e,q,c] = value


class HexOperator:
    def __init__(self, p, t, spacing, E=1000., nu=.35, device='cuda:0'):
        self.device = wp.get_device(device)
        if not self.device.is_cuda:
            raise ValueError('GPU adapter requires a CUDA device')
        self.p, self.t = np.asarray(p), np.asarray(t)
        assert self.p.ndim == 2 and self.p.shape[1] == 3 and np.isfinite(self.p).all()
        assert self.t.ndim == 2 and self.t.shape[1] == 8 and np.issubdtype(self.t.dtype,np.integer)
        assert self.t.min() >= 0 and self.t.max() < len(self.p)
        self.ndof = self.p.size
        self.spacing = np.asarray(spacing)
        for start in range(0,len(self.t),65536):
            points = self.p[self.t[start:start+65536]]
            if not np.allclose(points-points[:,:1],CORNERS*self.spacing,rtol=1e-10,atol=1e-10):
                raise ValueError('HexOperator requires aligned rectangular cells of the supplied uniform spacing')
        ke, self.B, self.C, self.q = element(spacing, E, nu)
        conn = (3*self.t[:,:,None]+np.arange(3)).reshape(-1,24)
        flat = conn.ravel()
        assert np.array_equal(np.unique(flat), np.arange(self.ndof))
        self.diag = np.bincount(flat, weights=np.tile(ke.diagonal(),len(t)), minlength=self.ndof)
        assert np.all(self.diag > 0)
        offsets = np.r_[0, np.cumsum(np.bincount(flat,minlength=self.ndof))]
        self.conn = wp.array(conn.astype(np.int32), dtype=wp.int32, device=self.device)
        self.offsets = wp.array(offsets.astype(np.int32), dtype=wp.int32, device=self.device)
        self.incidence = wp.array(np.argsort(flat,kind='stable').astype(np.int32), dtype=wp.int32, device=self.device)
        self.ke = wp.array(ke, dtype=wp.float64, device=self.device)
        self.cb = wp.array(np.einsum('ab,qbj->qaj',self.C,self.B), dtype=wp.float64, device=self.device)

    def operator(self, fixed=()):
        mask = np.zeros(self.ndof,dtype=np.int32)
        mask[np.asarray(fixed,dtype=int)] = 1
        flags = wp.array(mask,dtype=wp.int32,device=self.device)
        def mv(x,y,z,alpha,beta):
            wp.launch(multiply,dim=self.ndof,inputs=[self.conn,self.offsets,self.incidence,
                      self.ke,flags,x,y,z,alpha,beta],device=self.device)
        return LinearOperator((self.ndof,self.ndof),wp.float64,self.device,mv)

    def apply(self, u):
        x = wp.array(np.asarray(u,dtype=float),dtype=wp.float64,device=self.device)
        y = wp.zeros_like(x)
        self.operator().matvec(x,y,y,1.,0.)
        return y.numpy()

    def solve(self, f, fixed, prescribed=None, maxiter=5000):
        start = time.perf_counter()
        fixed = np.unique(fixed).astype(int)
        prescribed = np.zeros(self.ndof) if prescribed is None else np.asarray(prescribed,dtype=float)
        assert prescribed.shape == (self.ndof,)
        assert np.all(prescribed[np.setdiff1d(np.arange(self.ndof),fixed)] == 0)
        rhs = np.asarray(f,dtype=float)-self.apply(prescribed)
        rhs[fixed] = 0.
        inv = 1/self.diag
        inv[fixed] = 1.
        inv_gpu = wp.array(inv,dtype=wp.float64,device=self.device)
        def mv(x,y,z,alpha,beta):
            wp.launch(diagonal_multiply,dim=self.ndof,inputs=[inv_gpu,x,y,z,alpha,beta],device=self.device)
        M = LinearOperator((self.ndof,self.ndof),wp.float64,self.device,mv)
        b = wp.array(rhs,dtype=wp.float64,device=self.device)
        x = wp.zeros_like(b)
        iterations,error,tolerance = cg(self.operator(fixed),b,x,M=M,tol=1e-10,atol=1e-12,
                                        maxiter=maxiter,check_every=10)
        u = x.numpy()+prescribed
        reaction = self.apply(u)-f
        free = np.setdiff1d(np.arange(self.ndof),fixed)
        true_residual = float(np.linalg.norm(reaction[free])/max(np.linalg.norm(np.asarray(f)[free]), np.linalg.norm(rhs[free]),1e-30))
        if not np.isfinite(u).all() or error > tolerance or true_residual > 1e-8:
            raise RuntimeError(f'CG rejected: iterations={iterations}, recursive={error}, true_relative={true_residual}')
        return u,reaction,{"iterations":iterations,"recursive_residual":error,
                           "true_relative_free_residual":true_residual,
                           "elapsed_seconds":time.perf_counter()-start}

    def stress(self, u):
        ug = wp.array(u,dtype=wp.float64,device=self.device)
        result = wp.empty((len(self.t),8,6),dtype=wp.float64,device=self.device)
        wp.launch(recover,dim=result.shape,inputs=[self.conn,self.cb,ug,result],device=self.device)
        values = result.numpy()
        assert np.isfinite(values).all()
        return values

    def contact(self, f, base, wall_dofs, gap0):
        wall = np.asarray(wall_dofs,dtype=int)
        gap0 = np.asarray(gap0,dtype=float)
        assert len(wall) == len(gap0) and np.all(gap0 >= 0)
        assert len(np.unique(wall)) == len(wall) and not len(np.intersect1d(base,wall))
        active = np.flatnonzero(gap0 < 1e-12)
        history = []
        for step in range(40):
            fixed = np.union1d(base,wall[active])
            prescribed = np.zeros(self.ndof)
            prescribed[wall[active]] = -gap0[active]
            u,r,info = self.solve(f,fixed,prescribed)
            gaps = gap0+u[wall]
            new = np.flatnonzero(r[wall]-self.diag[wall]*gaps > 1e-8)
            history.append({"step":step,"active":len(active),"next_active":len(new),**info})
            if np.array_equal(active,new):
                assert gaps.min() >= -1e-8 and (len(active) == 0 or r[wall[active]].min() >= -1e-8)
                return u,r,gaps,active,history
            active = new
        raise RuntimeError('GPU wall contact did not converge')


def stress_tensors(stress):
    tensors = np.zeros((*stress.shape[:-1],3,3))
    for k,(i,j) in enumerate([(0,0),(1,1),(2,2),(0,1),(1,2),(0,2)]):
        tensors[...,i,j] = tensors[...,j,i] = stress[...,k]
    return tensors
