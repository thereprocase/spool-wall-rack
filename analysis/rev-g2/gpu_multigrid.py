"""GPU V-cycle from a PyAMG elasticity hierarchy; fine physics is unchanged.

PyAMG 5.3.0 (MIT) builds the auxiliary hierarchy on CPU. All V-cycle operations
and the surrounding fine solve execute on CUDA, including the small coarse
inverse. Three symmetric Jacobi sweeps use a certified row-sum damping bound.
"""
import time

import numpy as np
import pyamg
import warp as wp
from warp.optim.linear import LinearOperator

from gpu_coarse_geometry import build


@wp.kernel
def csr_apply(ptr:wp.array[int],col:wp.array[int],val:wp.array[wp.float64],
              x:wp.array[wp.float64],out:wp.array[wp.float64]):
    i=wp.tid()
    v=wp.float64(0.)
    for k in range(ptr[i],ptr[i+1]):
        v += val[k]*x[col[k]]
    out[i]=v


@wp.kernel
def relax(x:wp.array[wp.float64],rhs:wp.array[wp.float64],ax:wp.array[wp.float64],weight:wp.array[wp.float64]):
    i=wp.tid()
    x[i] += weight[i]*(rhs[i]-ax[i])


@wp.kernel
def residual(rhs:wp.array[wp.float64],ax:wp.array[wp.float64],out:wp.array[wp.float64]):
    i=wp.tid()
    out[i]=rhs[i]-ax[i]


@wp.kernel
def add(x:wp.array[wp.float64],increment:wp.array[wp.float64]):
    i=wp.tid()
    x[i] += increment[i]


@wp.kernel
def dense_apply(matrix:wp.array2d[wp.float64],x:wp.array[wp.float64],out:wp.array[wp.float64]):
    i=wp.tid()
    v=wp.float64(0.)
    for j in range(matrix.shape[1]):
        v += matrix[i,j]*x[j]
    out[i]=v


@wp.kernel
def restrict_free(ptr:wp.array[int],col:wp.array[int],val:wp.array[wp.float64],fixed:wp.array[int],
                  fine:wp.array[wp.float64],coarse:wp.array[wp.float64]):
    node,axis=wp.tid()
    v=wp.float64(0.)
    for k in range(ptr[node],ptr[node+1]):
        i=3*col[k]+axis
        if fixed[i] == 0:
            v += val[k]*fine[i]
    coarse[3*node+axis]=v


@wp.kernel
def additive_prolong(ptr:wp.array[int],col:wp.array[int],val:wp.array[wp.float64],fixed:wp.array[int],
                    inv:wp.array[wp.float64],coarse:wp.array[wp.float64],x:wp.array[wp.float64],
                    y:wp.array[wp.float64],out:wp.array[wp.float64],alpha:wp.float64,beta:wp.float64):
    node,axis=wp.tid()
    i=3*node+axis
    v=inv[i]*x[i]
    if fixed[i] == 0:
        for k in range(ptr[node],ptr[node+1]):
            v += val[k]*coarse[3*col[k]+axis]
    v *= alpha
    if beta != wp.float64(0.):
        v += beta*y[i]
    out[i]=v


def rigid_modes(p):
    relative=p-p.mean(axis=0)
    B=np.zeros((len(p),3,6))
    B[:,:,:3]=np.eye(3)
    B[:,:,3:]=np.cross(np.eye(3)[None,:,:],relative[:,None,:]).transpose(0,2,1)
    B=B.reshape(-1,6)
    B /= np.maximum(np.linalg.norm(B,axis=0),1e-30)
    return B


class GpuCSR:
    def __init__(self,A,device):
        A=A.tocsr();A.sort_indices()
        assert A.nnz < 2**31
        self.shape=A.shape;self.device=device
        self.arrays=[wp.array(v,dtype=dtype,device=device) for v,dtype in
                     [(A.indptr.astype(np.int32),wp.int32),(A.indices.astype(np.int32),wp.int32),(A.data,wp.float64)]]

    def apply(self,x,out):
        wp.launch(csr_apply,dim=self.shape[0],inputs=[*self.arrays,x,out],device=self.device)


class VCycle:
    def __init__(self,matrices,transfers,device,sweeps=3):
        self.device=device;self.sweeps=sweeps
        self.cpu_A=[A.tocsr() for A in matrices]
        self.cpu_P=[P.tocsr() for P in transfers]
        self.A=[GpuCSR(A,device) for A in self.cpu_A[:-1]]
        self.P=[GpuCSR(P,device) for P in self.cpu_P]
        self.R=[GpuCSR(P.T,device) for P in self.cpu_P]
        self.weights=[];self.wg=[];self.spectral_bounds=[]
        for A in self.cpu_A[:-1]:
            diagonal=A.diagonal()
            assert np.all(diagonal>0)
            # Gershgorin on D^-1/2 A D^-1/2 has the same spectrum as D^-1 A
            # without inflating the bound at tiny cut-material diagonals.
            root=1/np.sqrt(diagonal)
            bound=float(np.max(root*(abs(A) @ root)))
            self.spectral_bounds.append(bound)
            weight=(1./bound)/diagonal
            self.weights.append(weight)
            self.wg.append(wp.array(weight,dtype=wp.float64,device=device))
        last=self.cpu_A[-1].toarray()
        assert np.linalg.norm(last-last.T)/np.linalg.norm(last)<1e-10
        inverse_lower=np.linalg.solve(np.linalg.cholesky(.5*(last+last.T)),np.eye(len(last)))
        self.inverse=inverse_lower.T @ inverse_lower
        self.inverse_gpu=wp.array(self.inverse,dtype=wp.float64,device=device)
        self.x=[wp.zeros(A.shape[0],dtype=wp.float64,device=device) for A in self.cpu_A]
        self.rhs=[wp.zeros_like(x) for x in self.x]
        self.work=[wp.zeros_like(x) for x in self.x]
        self.r=[wp.zeros_like(x) for x in self.x]

    def cycle(self,level=0):
        x,b,work=self.x[level],self.rhs[level],self.work[level]
        if level==len(self.cpu_A)-1:
            wp.launch(dense_apply,dim=len(x),inputs=[self.inverse_gpu,b,x],device=self.device)
            return
        x.zero_()
        for _ in range(self.sweeps):
            self.A[level].apply(x,work)
            wp.launch(relax,dim=len(x),inputs=[x,b,work,self.wg[level]],device=self.device)
        self.A[level].apply(x,work)
        wp.launch(residual,dim=len(x),inputs=[b,work,self.r[level]],device=self.device)
        self.R[level].apply(self.r[level],self.rhs[level+1])
        self.cycle(level+1)
        self.P[level].apply(self.x[level+1],work)
        wp.launch(add,dim=len(x),inputs=[x,work],device=self.device)
        for _ in range(self.sweeps):
            self.A[level].apply(x,work)
            wp.launch(relax,dim=len(x),inputs=[x,b,work,self.wg[level]],device=self.device)

    def cpu_cycle(self,b,level=0):
        if level==len(self.cpu_A)-1:
            return self.inverse @ b
        A,P=self.cpu_A[level],self.cpu_P[level]
        x=np.zeros_like(b)
        for _ in range(self.sweeps):
            x += self.weights[level]*(b-A @ x)
        x += P @ self.cpu_cycle(P.T @ (b-A @ x),level+1)
        for _ in range(self.sweeps):
            x += self.weights[level]*(b-A @ x)
        return x


class CoarseCorrection:
    def __init__(self,op,p,master,origin,ratio,fixed,enabled=None,progress=lambda x:None,sweeps=3):
        start=time.perf_counter()
        A,Q,pc,self.report=build(p,op.t,op.scale,op.P,master,op.spacing,origin,ratio,fixed,enabled,progress)
        self.Q=Q;self.fixed=np.unique(fixed).astype(int)
        B=rigid_modes(pc)
        B[self.report['identically_zero_projected_coarse_dofs']]=0.
        mg_start=time.perf_counter()
        hierarchy=pyamg.smoothed_aggregation_solver(A.tobsr(blocksize=(3,3)),B=B,
                    symmetry='symmetric',strength=('symmetric',{'theta':0.}),
                    smooth=('jacobi',{'omega':4./3.}),improve_candidates=None,
                    max_coarse=96,max_levels=15,keep=False)
        matrices=[level.A.tocsr() for level in hierarchy.levels]
        transfers=[level.P.tocsr() for level in hierarchy.levels[:-1]]
        self.report['amg_setup_seconds']=time.perf_counter()-mg_start
        self.report['levels']=[{'dofs':m.shape[0],'nnz':m.nnz} for m in matrices]
        self.report['pyamg_version']=pyamg.__version__
        progress({'stage':'amg_hierarchy',**{k:self.report[k] for k in ['amg_setup_seconds','levels']}})
        self.cycle=VCycle(matrices,transfers,op.device,sweeps)
        self.report['jacobi_spectral_upper_bounds']=self.cycle.spectral_bounds
        self.qg,self.qtg=GpuCSR(Q,op.device),GpuCSR(Q.T,op.device)
        flags=np.zeros(op.ndof,dtype=np.int32);flags[self.fixed]=1
        self.flags=wp.array(flags,dtype=wp.int32,device=op.device)
        self.inv=1/op.diag;self.inv[self.fixed]=1.
        self.ig=wp.array(self.inv,dtype=wp.float64,device=op.device)
        self.op=op
        self.report['total_setup_seconds']=time.perf_counter()-start

    def operator(self):
        def mv(x,y,z,alpha,beta):
            wp.launch(restrict_free,dim=(self.Q.shape[1],3),inputs=[*self.qtg.arrays,self.flags,x,self.cycle.rhs[0]],device=self.op.device)
            self.cycle.cycle()
            wp.launch(additive_prolong,dim=(self.Q.shape[0],3),inputs=[*self.qg.arrays,self.flags,self.ig,self.cycle.x[0],x,y,z,alpha,beta],device=self.op.device)
        return LinearOperator((self.op.ndof,self.op.ndof),wp.float64,self.op.device,mv)

    def cpu_apply(self,x):
        masked=x.copy();masked[self.fixed]=0
        coarse_rhs=np.asarray(self.Q.T @ masked.reshape(-1,3)).ravel()
        coarse=self.cycle.cpu_cycle(coarse_rhs)
        result=np.asarray(self.Q @ coarse.reshape(-1,3)).ravel()
        result[self.fixed]=0.
        return result+self.inv*x
