"""G seat, washer, bore and unilateral wall interfaces on inscribed voxels.

No component is discarded. Unsupported loaded fragments are an explicit failed
load case rather than an excuse to add artificial restraints.
"""
from pathlib import Path
import argparse
import json

import numpy as np

from solve_plastic import interface_loads


def classify(data,total=117.72):
    p,t = data['p'],data['t']
    faces,normal,area = data['faces'],data['normal'],data['area']
    h = data['spacing']
    centers = p[faces].mean(axis=1)
    f = np.zeros_like(p)
    patches = {}
    for x,y,name in [(90.,0.,'rear_seat'),(190.,12.,'front_seat')]:
        target = interface_loads(total)[name]
        radial = centers[:,:2]-[x,y]
        radius = np.linalg.norm(radial,axis=1)
        direction = radial/np.maximum(radius[:,None],1e-30)
        angle = np.arctan2(direction[:,1],direction[:,0])-np.arctan2(target[1],target[0])
        angle = np.arctan2(np.sin(angle),np.cos(angle))
        inward = -(normal[:,:2]*direction).sum(axis=1)
        selected = ((radius >= 12.99)&(radius <= 13+np.linalg.norm(h[:2])+.02)
                    &(abs(angle) <= np.deg2rad(25))&(normal[:,2] == 0)&(inward > .05))
        ids = np.flatnonzero(selected)
        assert len(ids),f'Missing {name} interface'
        weights = area[ids]*inward[ids]
        # Each face force is radial through the dowel centre. Solve two force
        # constraints while keeping a positive pressure over the selected arc.
        directions = direction[ids]
        coefficients = np.linalg.solve(np.einsum('i,ij,ik->jk',weights,directions,directions),target[:2])
        from scipy.optimize import least_squares
        def pressure_force(coeff):
            return (directions*(weights*np.maximum(directions @ coeff,0.))[:,None]).sum(axis=0)-target[:2]
        def pressure_jacobian(coeff):
            active = (directions @ coeff) > 0
            return np.einsum('i,ij,ik->jk',weights[active],directions[active],directions[active])
        pressure = least_squares(pressure_force,coefficients,jac=pressure_jacobian,
                                 xtol=1e-13,ftol=1e-13,gtol=1e-13,max_nfev=100)
        magnitude = weights*np.maximum(directions @ pressure.x,0.)
        assert np.linalg.norm(pressure_force(pressure.x)) < 1e-8,'Resolved seat normals cannot support target force without tension'
        traction = np.column_stack([directions*magnitude[:,None],np.zeros(len(ids))])
        for corner in range(4):
            np.add.at(f,faces[ids,corner],traction/4)
        force = traction.sum(axis=0)
        z_moment = np.cross(np.column_stack([radial[ids],np.zeros(len(ids))]),traction).sum(axis=0)[2]
        assert np.linalg.norm(force-target) < 1e-8 and abs(z_moment) < 1e-8
        patches[name] = {'faces':ids,'nodes':np.unique(faces[ids]),'face_force':traction,
                         'target_force_N':target.tolist(),'applied_force_N':force.tolist(),
                         'bearing_axis_moment_Nmm':float(z_moment),'projected_area_mm2':float(weights.sum())}
    base,heads,bores,hardware = [],{}, {},{}
    for y in [164.,40.]:
        radial = centers[:,1:]-[y,12.]
        radius = np.linalg.norm(radial,axis=1)
        candidate = ((normal[:,0] == 1)&(centers[:,0] <= 3.6+1e-8)&(centers[:,0] >= 3.6-h[0]-.02)
                     &(radius > 2.75)&(radius < 6.5))
        assert candidate.any(),f'Missing washer face {y}'
        front = centers[candidate,0].max()
        mask = candidate & np.isclose(centers[:,0],front,atol=1e-9,rtol=0)
        head = np.unique(faces[mask])
        nodal_radius = np.linalg.norm(p[head,1:]-[y,12.],axis=1)
        head = head[(nodal_radius > 2.75)&(nodal_radius < 6.5)]
        inward = -(normal[:,1:]*radial).sum(axis=1)/np.maximum(radius,1e-30)
        bore_mask = ((centers[:,0] < 3.6+1e-8)&(normal[:,0] == 0)&(radius >= 2.59)
                     &(radius <= 2.6+np.linalg.norm(h[1:])+.02)&(inward > .05))
        bore = np.unique(faces[bore_mask])
        assert len(head) and len(bore),f'Missing fixing {y}'
        base.extend(3*head)
        base.extend(3*bore+1)
        base.extend(3*bore+2)
        key = str(int(y))
        heads[key],bores[key] = head,bore
        hardware[key] = {'washer_nodes':len(head),'bore_nodes':len(bore),'nominal_washer_plane_x_mm':3.6,
                         'selected_material_plane_x_mm':float(front),'washer_plane_retreat_mm':float(3.6-front),
                         'washer_face_area_mm2':float(area[mask].sum()),'bore_face_area_mm2':float(area[bore_mask].sum())}
    base = np.unique(base).astype(int)
    wall_faces = (normal[:,0] == -1)&(centers[:,0] <= 3.6+1e-8)
    wall = np.unique(faces[wall_faces])
    wall = wall[~np.isin(3*wall,base)]
    assert len(wall)
    # Nominal installation wall is X=0. Source polygonization has a 0.0005 mm
    # offset; retained full cells all lie at or in front of this plane.
    gap = p[wall,0].copy()
    assert gap.min() >= -1e-8
    gap = np.maximum(gap,0.)
    node_component = np.full(len(p),-1,dtype=np.int32)
    for corner in range(8):
        node_component[t[:,corner]] = data['component']
    assert np.all(node_component[t] == data['component'][:,None])
    ncomp = int(data['component'].max())+1
    centroid = np.zeros((ncomp,3))
    np.add.at(centroid,node_component,p)
    centroid /= np.bincount(node_component)[:,None]
    relative_p = p-centroid[node_component]
    rigid_load = np.zeros((ncomp,6))
    np.add.at(rigid_load[:,:3],node_component,f)
    np.add.at(rigid_load[:,3:],node_component,np.cross(relative_p,f))
    restrained_nodes,axis = base//3,base%3
    directions = np.eye(3)[axis]
    rows = np.column_stack([directions,np.cross(relative_p[restrained_nodes],directions)])
    gram = np.zeros((ncomp,6,6))
    np.add.at(gram,node_component[restrained_nodes],np.einsum('ij,ik->ijk',rows,rows))
    values,vectors = np.linalg.eigh(gram)
    null = values < np.maximum(values[:,-1,None],1.)*1e-10
    projections = np.einsum('nji,nj->ni',vectors,rigid_load)*null
    unsupported = np.linalg.norm(projections,axis=1)
    # Ignore a rigid mode only when it has zero external virtual work, never
    # by pinning or deleting a disconnected element. Wall contact supplies X
    # reactions; it cannot repair an unsupported net vertical force.
    bad = np.flatnonzero(unsupported > 1e-7)
    loaded = np.flatnonzero(np.bincount(node_component,weights=np.linalg.norm(f,axis=1)) > 1e-10)
    report = {'load_N':total,'applied_force_N':f.sum(axis=0).tolist(),
              'applied_moment_Nmm':np.cross(p,f).sum(axis=0).tolist(),
              'bearing_interfaces':{name:{k:v for k,v in patch.items() if k not in ['faces','nodes','face_force']} for name,patch in patches.items()},
              'hardware':hardware,'wall_nodes':len(wall),'minimum_initial_gap_mm':float(gap.min()),
              'maximum_initial_gap_mm':float(gap.max()),'base_fixed_dofs':len(base),
              'loaded_components':loaded.tolist(),'unsupported_loaded_components':bad.tolist(),
              'maximum_unsupported_rigid_load':float(unsupported.max()),
              'component_rigid_constraint_ranks':np.count_nonzero(~null,axis=1).tolist(),
              'status':'PASS_INTERFACE_PRECHECK' if not len(bad) else 'FAIL_UNSUPPORTED_LOADED_MATERIAL',
              'model':'Rigid washer axial restraint and rigid bore lateral restraint. Radial, nonnegative dowel bearing tractions reproduce the reference force split and zero moment about each dowel axis. Wall normal contact preserves voxel surface gaps. Hardware/substrate capacity is unqualified.'}
    return {'f':f.ravel(),'base':base,'wall':wall,'gap':gap,'node_component':node_component,
            'patches':patches,'heads':heads,'bores':bores,'report':report}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--geometry',type=Path,required=True)
    args = ap.parse_args()
    with np.load(args.geometry/'geometry.npz') as data:
        result = classify(data)
    report = result['report']
    (args.geometry/'interfaces.json').write_text(json.dumps(report,indent=2)+'\n')
    np.savez(args.geometry/'interfaces.npz',**{k:result[k] for k in ['f','base','wall','gap','node_component']},
             **{name+'_nodes':p['nodes'] for name,p in result['patches'].items()})
    print(json.dumps({k:report[k] for k in ['status','applied_force_N','loaded_components','unsupported_loaded_components','maximum_unsupported_rigid_load','wall_nodes','hardware']},indent=2),flush=True)


if __name__ == '__main__':
    main()
