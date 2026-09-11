"""Matrix-free CUDA elasticity on constrained two-level hex leaves.

Applies P.T K P; P interpolates hanging nodes. Every leaf contributes, with
eight Gauss points per leaf. This adapter uses a diagonal preconditioner only.
"""
import time

import numpy as np
import warp as wp
from warp.optim.linear import LinearOperator, cg

from gpu_hex import element, diagonal_multiply


@wp.kernel
def expand(ptr:wp.array[int], col:wp.array[int], val:wp.array[wp.float64],
           fixed:wp.array[int], x:wp.array[wp.float64], out:wp.array[wp.float64]):
    node,axis = wp.tid()
    value = wp.float64(0.)
    for k in range(ptr[node],ptr[node+1]):
        j = 3*col[k]+axis
        if fixed[j] == 0:
            value += val[k]*x[j]
    out[3*node+axis] = value


@wp.kernel
def leaf_multiply(t:wp.array2d[int], scale:wp.array[int], ke:wp.array2d[wp.float64],
                  x:wp.array[wp.float64], out:wp.array[wp.float64]):
    e,row = wp.tid()
    value = wp.float64(0.)
    for col in range(24):
        value += ke[row,col]*x[3*t[e,col//3]+col%3]
    wp.atomic_add(out,3*t[e,row//3]+row%3,value*wp.float64(scale[e]))


@wp.kernel
def restrict(ptr:wp.array[int],col:wp.array[int],val:wp.array[wp.float64],
             fixed:wp.array[int], full:wp.array[wp.float64], x:wp.array[wp.float64],
             y:wp.array[wp.float64], z:wp.array[wp.float64], alpha:wp.float64,beta:wp.float64):
    node,axis = wp.tid()
    i = 3*node+axis
    value = wp.float64(0.)
    if fixed[i] != 0:
        value = x[i]
    else:
        for k in range(ptr[node],ptr[node+1]):
            value += val[k]*full[3*col[k]+axis]
    result = alpha*value
    if beta != wp.float64(0.):
        result += beta*y[i]
    z[i] = result


class AdaptiveOperator:
    def __init__(self,t,scale,P,spacing,device='cuda:0'):
        start = time.perf_counter()
        self.device = wp.get_device(device)
        assert self.device.is_cuda
        self.P,self.t,self.scale,self.spacing = P,t,scale,np.asarray(spacing)
        self.ndof = 3*P.shape[1]
        ke,self.B,self.C,self.q = element(spacing)
        self.ke_cpu = ke
        self.tg = wp.array(t,dtype=wp.int32,device=self.device)
        self.sg = wp.array(scale.astype(np.int32),dtype=wp.int32,device=self.device)
        self.kg = wp.array(ke,dtype=wp.float64,device=self.device)
        def gpu_csr(matrix):
            return [wp.array(a,dtype=dtype,device=self.device) for a,dtype in
                    [(matrix.indptr,wp.int32),(matrix.indices,wp.int32),(matrix.data,wp.float64)]]
        self.pg = gpu_csr(P)
        self.ptg = gpu_csr(P.T.tocsr())
        self.expanded = wp.zeros(3*P.shape[0],dtype=wp.float64,device=self.device)
        self.full_result = wp.zeros_like(self.expanded)
        # Positive diagonal approximation; cross terms from condensation are
        # omitted in M only, never in the actual stiffness operator.
        diagonal = np.zeros((P.shape[0],3))
        for c in range(8):
            for axis in range(3):
                diagonal[:,axis] += np.bincount(t[:,c],weights=scale*ke[3*c+axis,3*c+axis],minlength=P.shape[0])
        self.diag = np.asarray(P.power(2).T @ diagonal).ravel()
        assert np.all(self.diag > 0)
        self.setup_seconds = time.perf_counter()-start

    def operator(self,fixed=()):
        mask = np.zeros(self.ndof,dtype=np.int32)
        mask[np.asarray(fixed,dtype=int)] = 1
        flags = wp.array(mask,dtype=wp.int32,device=self.device)
        def mv(x,y,z,alpha,beta):
            wp.launch(expand,dim=(self.P.shape[0],3),inputs=[*self.pg,flags,x,self.expanded],device=self.device)
            self.full_result.zero_()
            wp.launch(leaf_multiply,dim=(len(self.t),24),inputs=[self.tg,self.sg,self.kg,self.expanded,self.full_result],device=self.device)
            wp.launch(restrict,dim=(self.P.shape[1],3),inputs=[*self.ptg,flags,self.full_result,x,y,z,alpha,beta],device=self.device)
        return LinearOperator((self.ndof,self.ndof),wp.float64,self.device,mv)

    def apply(self,u,fixed=()):
        x = wp.array(u,dtype=wp.float64,device=self.device)
        result = wp.zeros_like(x)
        self.operator(fixed).matvec(x,result,result,1.,0.)
        return result.numpy()

    def solve(self,f,fixed,prescribed=None,maxiter=1000,callback=None,max_seconds=240,initial=None):
        start = time.perf_counter()
        fixed = np.unique(fixed).astype(int)
        prescribed = np.zeros(self.ndof) if prescribed is None else prescribed
        rhs = f-self.apply(prescribed)
        rhs[fixed] = 0.
        inv = 1/self.diag
        inv[fixed] = 1.
        ig = wp.array(inv,dtype=wp.float64,device=self.device)
        def mv(x,y,z,alpha,beta):
            wp.launch(diagonal_multiply,dim=self.ndof,inputs=[ig,x,y,z,alpha,beta],device=self.device)
        M = LinearOperator((self.ndof,self.ndof),wp.float64,self.device,mv)
        b = wp.array(rhs,dtype=wp.float64,device=self.device)
        guess = np.zeros(self.ndof) if initial is None else np.asarray(initial)-prescribed
        guess[fixed] = 0.
        x = wp.array(guess,dtype=wp.float64,device=self.device)
        latest = [0,float('inf'),0.]
        def observe(iterations,error,tolerance):
            latest[:] = [iterations,error,tolerance]
            if callback is not None:
                callback(iterations,error,tolerance)
            if time.perf_counter()-start > max_seconds:
                raise TimeoutError('Bounded GPU solve exceeded its time budget')
        budget_stop = False
        try:
            iterations,error,tolerance = cg(self.operator(fixed),b,x,M=M,tol=1e-10,atol=1e-12,
                                            maxiter=maxiter,check_every=20,callback=observe)
        except TimeoutError:
            iterations,error,tolerance = latest
            budget_stop = True
        u = x.numpy()+prescribed
        reaction = self.apply(u)-f
        free = np.ones(self.ndof,dtype=bool)
        free[fixed] = False
        relative = float(np.linalg.norm(reaction[free])/max(np.linalg.norm(rhs[free]),np.linalg.norm(f[free]),1e-30))
        passed = bool(np.isfinite(u).all() and error <= tolerance and relative < 1e-8)
        # Failure returns the entire iterate and raw residual for preservation.
        return u,reaction,{'status':'PASS_LINEAR_SOLVE' if passed else 'FAIL_LINEAR_CONVERGENCE',
                           'iterations':iterations,'recursive_residual':error,'tolerance':tolerance,
                           'stopped_by_time_budget':budget_stop,
                           'true_relative_free_residual':relative,'elapsed_seconds':time.perf_counter()-start}

    def stress_chunks(self,u,chunk=32768):
        full = np.asarray(self.P @ u.reshape(-1,3))
        cb = np.einsum('ab,qbj->qaj',self.C,self.B)
        for begin in range(0,len(self.t),chunk):
            v = full[self.t[begin:begin+chunk]].reshape(-1,24)
            stress = np.einsum('qaj,ej->eqa',cb,v)/self.scale[begin:begin+chunk,None,None]
            assert np.isfinite(stress).all()
            yield begin,stress
