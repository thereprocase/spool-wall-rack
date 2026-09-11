"""Exact Galerkin coarse space over actual adaptive hex material.

Coarse Q1 basis functions accelerate the solver only; the fine operator and
material remain unchanged. Integrate the coarse gradient products over every
actual leaf using polynomial moments, then apply exact fixed-DOF corrections.
Disconnected inactive components keep their original fine operator.
"""
from itertools import product
import time

import numpy as np
from scipy.sparse import coo_matrix, csr_matrix,diags

from gpu_hex import CORNERS,element


POWERS = np.array(list(product(range(3),repeat=3)))


def stiffness_polynomials(H):
    powers = np.array(list(product(range(2),repeat=3)))
    B = np.zeros((8,6,24))
    for c,corner in enumerate(CORNERS):
        for axis in range(3):
            for k,power in enumerate(powers):
                if power[axis]:
                    continue
                value = (2*corner[axis]-1)/H[axis]
                for a in range(3):
                    if a != axis:
                        value *= 2*corner[a]-1 if power[a] else 1-corner[a]
                for row,component in {0:[(0,0),(3,1),(5,2)],
                                      1:[(1,1),(3,0),(4,2)],
                                      2:[(2,2),(4,1),(5,0)]}[axis]:
                    B[k,row,3*c+component] += value
    _,_,C,_ = element(H)
    coefficients = np.zeros((27,24,24))
    for i,a in enumerate(powers):
        for j,b in enumerate(powers):
            k = np.ravel_multi_index(a+b,(3,3,3))
            coefficients[k] += B[i].T @ C @ B[j]
    return coefficients


def shape_values(normalized):
    return np.prod(np.where(CORNERS[None] == 1,normalized[:,None,:],1-normalized[:,None,:]),axis=2)


def build(p,t,scale,P,master,spacing,origin,ratio,fixed,enabled=None,progress=lambda x:None):
    start = time.perf_counter()
    spacing,origin = np.asarray(spacing),np.asarray(origin)
    assert ratio >= 2 and (ratio & (ratio-1)) == 0
    H = spacing*ratio
    enabled = np.ones(len(master),dtype=bool) if enabled is None else np.asarray(enabled,dtype=bool)
    enabled_full = np.asarray(P @ enabled.astype(float)).ravel()
    assert np.all((enabled_full < 1e-12)|(enabled_full > 1-1e-12)), 'A material component must be enabled as a whole'
    leaf_enabled = enabled_full[t[:,0]] > .5
    assert np.all((enabled_full[t] > .5) == leaf_enabled[:,None])
    leaves = np.flatnonzero(leaf_enabled)
    cells = np.rint((p[t[leaves,0]]-origin)/spacing).astype(np.int32)
    assert np.all(cells%ratio+scale[leaves,None] <= ratio), 'Coarse grid must align with leaf faces'
    macro,which = np.unique(cells//ratio,axis=0,return_inverse=True)
    vertices,inverse = np.unique((macro[:,None,:]+CORNERS).reshape(-1,3),axis=0,return_inverse=True)
    macro_t = inverse.reshape(-1,8).astype(np.int32)
    grid_shape = vertices.max(axis=0)+2
    keys = np.ravel_multi_index(vertices.T,grid_shape)
    pm = p[master]
    lattice=np.rint((pm-origin)/spacing).astype(np.int32)
    assert np.max(abs(lattice*spacing+origin-pm))<1e-9
    # Use exact lattice indices. Floating subtraction at a distant grid face
    # can otherwise manufacture a tiny positive weight on an absent cell.
    node_cell=lattice//ratio
    local=(lattice%ratio)/ratio
    rows,columns,weights = [],[],[]
    values = shape_values(local)
    for c,offset in enumerate(CORNERS):
        chosen = np.flatnonzero((values[:,c] > 1e-14)&enabled)
        query = np.ravel_multi_index((node_cell[chosen]+offset).T,grid_shape)
        column = np.searchsorted(keys,query)
        assert np.all(column < len(keys)) and np.array_equal(keys[column],query)
        rows.append(chosen);columns.append(column);weights.append(values[chosen,c])
    Q = coo_matrix((np.concatenate(weights),(np.concatenate(rows),np.concatenate(columns))),
                   shape=(len(master),len(vertices))).tocsr()
    assert np.max(abs(Q @ (vertices*H+origin)-pm)*enabled[:,None]) < 1e-8
    assert np.max(abs(np.asarray(Q.sum(axis=1)).ravel()-enabled)) < 1e-12
    progress({'stage':'coarse_basis','cells':len(macro),'nodes':len(vertices),'Q_nnz':Q.nnz})
    center=(cells%ratio+scale[leaves,None]/2)/ratio
    variance=(scale[leaves]/ratio)**2/12
    powers=[np.ones_like(center),center,center*center+variance[:,None]]
    volumes=np.prod(spacing)*scale[leaves].astype(float)**3
    moments=np.empty((len(macro),27))
    for k,(a,b,c) in enumerate(POWERS):
        w=volumes*powers[a][:,0]*powers[b][:,1]*powers[c][:,2]
        moments[:,k]=np.bincount(which,weights=w,minlength=len(macro))
    K=(moments @ stiffness_polynomials(H).reshape(27,576)).reshape(-1,24,24)
    progress({'stage':'coarse_moments','represented_volume_mm3':float(moments[:,0].sum())})
    # Q_full = P Q on an aligned grid. Setting independent fixed DOFs to zero
    # subtracts P[:,fixed_nodes] Q[fixed_nodes,:] for each vector component.
    fixed=np.unique(fixed).astype(int)
    delta=[]
    affected_nodes=np.zeros(len(p),dtype=bool)
    for axis in range(3):
        nodes=fixed[fixed%3 == axis]//3
        d=(P[:,nodes] @ Q[nodes]).tocsr()
        delta.append(d)
        affected_nodes |= np.diff(d.indptr) > 0
    affected=np.flatnonzero(np.any(affected_nodes[t[leaves]],axis=1))
    ke,_,_,_=element(spacing)
    for begin in range(0,len(affected),1024):
        selected=affected[begin:begin+1024]
        lt=t[leaves[selected]]
        nc=macro_t[which[selected]]
        normalized=(p[lt]-origin-macro[which[selected],None,:]*H)/H
        phi=shape_values(normalized.reshape(-1,3)).reshape(-1,8,8)
        W0=np.einsum('eij,ab->eiajb',phi,np.eye(3)).reshape(-1,24,24)
        W=W0.copy()
        for axis in range(3):
            for c in range(8):
                correction=np.asarray(delta[axis][lt.ravel(),np.repeat(nc[:,c],8)]).reshape(-1,8)
                W[:,3*np.arange(8)+axis,3*c+axis] -= correction
        change=(W.transpose(0,2,1) @ ke @ W-W0.transpose(0,2,1) @ ke @ W0)*scale[leaves[selected],None,None]
        np.add.at(K,which[selected],change)
    progress({'stage':'coarse_constraints','affected_leaves':len(affected)})
    dofs=(3*macro_t[:,:,None]+np.arange(3,dtype=np.int32)).reshape(-1,24)
    rows=np.repeat(dofs,24,axis=1).ravel()
    columns=np.tile(dofs,(1,24)).ravel()
    A=coo_matrix((K.ravel(),(rows,columns)),shape=(3*len(vertices),)*2).tocsr()
    A.sum_duplicates();A.eliminate_zeros()
    asymmetry=A-A.T
    symmetry_error=float(np.max(abs(asymmetry.data),initial=0)/np.max(abs(A.data)))
    assert symmetry_error < 1e-10,symmetry_error
    # Roundoff symmetrization, after checking its size; no diagonal shift or
    # ersatz stiffness is inserted to hide a singular or indefinite operator.
    A=(.5*(A+A.T)).tocsr()
    free_mask=np.ones((len(master),3));free_mask.ravel()[fixed]=0
    norms=np.asarray(Q.power(2).T @ free_mask).ravel()
    inactive=np.flatnonzero(norms == 0)
    if len(inactive):
        # These basis columns are identically zero AFTER the fixed-DOF
        # projection, not physical rigid modes. Decouple their auxiliary
        # coefficients exactly and set unit diagonal; they never act on fine
        # material or receive a restricted residual.
        assert np.max(abs(A[inactive].data),initial=0) < np.max(abs(A.data))*1e-10
        keep=np.ones(A.shape[0]);keep[inactive]=0
        A=(A.multiply(keep[:,None]).multiply(keep[None,:])+diags(1-keep)).tocsr()
    assert np.all(A.diagonal() > 0), 'Nonzero coarse basis has a nonpositive diagonal'
    report={'coarse_nodes':len(vertices),'coarse_cells':len(macro),'coarse_dofs':A.shape[0],
            'coarse_matrix_nnz':A.nnz,'ratio':ratio,'coarse_spacing_mm':H.tolist(),
            'represented_volume_mm3':float(moments[:,0].sum()),'affected_constraint_leaves':len(affected),
            'symmetry_error_before_roundoff_symmetrization':symmetry_error,
            'identically_zero_projected_coarse_dofs':inactive.tolist(),
            'build_seconds':time.perf_counter()-start,'policy':'Exact Galerkin coarse correction over included fine components. Fine material, gaps, constraints and operator are unchanged; no void or bridge stiffness.'}
    return A,Q,vertices*H+origin,report
