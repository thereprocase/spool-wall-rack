"""Audit and plot saved G fields without altering or dropping stress samples."""
from pathlib import Path
import argparse, json
import numpy as np
from scipy.sparse import load_npz
from gpu_hex import element, stress_tensors


def audit(geometry, adaptive, result, output, compare=None, label='Rev G'):
    output.mkdir(parents=True, exist_ok=False)
    report = json.loads((result/'solve.json').read_text())
    with np.load(geometry/'geometry.npz') as d:
        p, spacing = d['p'], d['spacing']
    with np.load(adaptive/'adaptive.npz') as d:
        t, scale, master = d['t'], d['scale'], d['master']
    P = load_npz(adaptive/'prolongation.npz')
    pm = p[master]
    mapping = np.full(len(p), -1, dtype=np.int32)
    mapping[master] = np.arange(len(master))
    with np.load(geometry/'interfaces.npz') as d:
        wall = 3*mapping[d['wall']]
        base = 3*mapping[d['base']//3]+d['base']%3
        seat_nodes = {k:mapping[d[k+'_nodes']] for k in ['rear_seat','front_seat']}
    state = result/f"contact-{report['contact_history'][-1]['contact_step']:02d}"
    u, r, f = [np.load(state/(k+'.npy')) for k in ['master_u','master_reaction','master_force']]
    fixed, active, gaps = [np.load(state/(k+'.npy')) for k in ['fixed_dofs','active_wall_indices','wall_gaps']]
    reaction = np.zeros_like(r); reaction[fixed] = r[fixed]
    balance = (f+reaction).reshape(-1,3)
    force_error = balance.sum(axis=0)
    moment_error = np.cross(pm,balance).sum(axis=0)
    full_u = np.asarray(P @ u.reshape(-1,3))
    magnitude = np.linalg.norm(full_u,axis=1)
    imax = int(magnitude.argmax())
    seats = {}
    for name, nodes in seat_nodes.items():
        assert np.all(nodes>=0)
        weights = np.linalg.norm(f.reshape(-1,3)[nodes],axis=1)
        seats[name] = {'mean_displacement_mm':u.reshape(-1,3)[nodes].mean(axis=0).tolist(),
                       'load_weighted_displacement_mm':np.average(u.reshape(-1,3)[nodes],axis=0,weights=weights).tolist(),
                       'maximum_resultant_displacement_mm':float(np.linalg.norm(u.reshape(-1,3)[nodes],axis=1).max())}
    evidence = {'source_result':result.name,'status':report['status'],'load_N':report['load_N'],
                'maximum_resultant_displacement_mm':float(magnitude[imax]),'maximum_displacement_position_mm':p[imax].tolist(),
                'seat_displacements':seats,'force_balance_error_N':force_error.tolist(),
                'moment_balance_error_Nmm':moment_error.tolist(),'minimum_wall_gap_mm':float(gaps.min()),
                'minimum_active_wall_reaction_N':float(r[wall[active]].min()) if len(active) else 0.,
                'total_wall_reaction_N':float(r[wall[active]].sum()),'active_wall_nodes':len(active),
                'compliance_Nmm':float(f@u),'solver_true_relative_free_residual':report['contact_history'][-1]['true_relative_free_residual'],
                'contact_steps':len(report['contact_history']),'elapsed_seconds':report['elapsed_seconds'],
                'geometry_omission_fraction':json.loads((geometry/'geometry.json').read_text()).get('omitted_fraction')}
    hardware = {}
    for height in [40.,164.]:
        selected = base[abs(pm[base//3,1]-height)<8.]
        nodal = np.zeros_like(r);nodal[selected]=r[selected]
        hardware[str(int(height))] = {'force_N':nodal.reshape(-1,3).sum(axis=0).tolist(),
                    'moment_about_fixing_center_Nmm':np.cross(pm-[3.6,height,12.],nodal.reshape(-1,3)).sum(axis=0).tolist()}
    evidence['idealized_fixing_reactions']=hardware
    evidence['contact_inequality_gate_passed']=bool(gaps.min(initial=0)>=-1e-8 and r[wall[active]].min(initial=0)>=-1e-8)
    evidence['force_balance_relative_error']=float(np.linalg.norm(force_error)/report['load_N'])
    applied_moment=np.cross(pm,f.reshape(-1,3)).sum(axis=0)
    evidence['moment_balance_relative_error']=float(np.linalg.norm(moment_error)/max(np.linalg.norm(applied_moment),1e-30))
    # Every sample contributes to its leaf maximum. The 0.5 mm display bins
    # contain maxima of leaves whose centers fall there, projected through Z.
    pixel = .5
    low = np.floor(p[:,:2].min(axis=0)/pixel)*pixel
    shape = np.ceil((p[:,:2].max(axis=0)-low)/pixel).astype(int)+1
    disp_image = np.full(tuple(shape),np.nan)
    ij = np.floor((p[:,:2]-low)/pixel).astype(int)
    np.fmax.at(disp_image,(ij[:,0],ij[:,1]),magnitude)
    stress_image = np.full(tuple(shape),np.nan)
    q = element(spacing)[3]
    peak = -np.inf
    count = 0
    comparison = None
    if compare:
        prior = sorted(compare.glob('contact-*'))[-1]
        previous_u = np.load(prior/'master_u.npy')
        delta = np.asarray(P @ (u-previous_u).reshape(-1,3))
        comparison = {'previous_result':compare.name,'maximum_nodal_displacement_change_mm':float(np.linalg.norm(delta,axis=1).max()),
                      'relative_displacement_l2_change':float(np.linalg.norm(delta)/max(np.linalg.norm(full_u),1e-30)),
                      'maximum_stress_component_change_MPa':0.,
                      'interpretation':'Observed iterate or load sensitivity, not a certified discretization error bound.'}
    for field in report['stress_fields']:
        begin = field['first_leaf']; stress = np.load(result/field['file'])
        assert np.isfinite(stress).all()
        principal = np.linalg.eigvalsh(stress_tensors(stress))[:,:,-1]
        e, g = np.unravel_index(principal.argmax(),principal.shape)
        if principal[e,g] > peak:
            peak = float(principal[e,g]); cell = begin+e
            position = p[t[cell,0]]+q[g]*scale[cell]
            evidence['raw_tensile_peak'] = {'MPa':peak,'leaf_index':int(cell),'gauss_index':int(g),'position_mm':position.tolist()}
        centers = p[t[begin:begin+len(stress),0]]+.5*spacing*scale[begin:begin+len(stress),None]
        xy = np.floor((centers[:,:2]-low)/pixel).astype(int)
        np.fmax.at(stress_image,(xy[:,0],xy[:,1]),principal.max(axis=1))
        count += stress.shape[0]*stress.shape[1]
        if comparison:
            previous = np.load(compare/field['file'])
            assert previous.shape==stress.shape
            comparison['maximum_stress_component_change_MPa'] = max(comparison['maximum_stress_component_change_MPa'],float(abs(stress-previous).max()))
    assert count==8*len(t)
    assert np.isclose(peak,report['raw_tensile_peak_MPa'],rtol=1e-12)
    evidence['retained_stress_samples']=count
    evidence['raw_von_mises_peak_MPa']=report['raw_von_mises_peak_MPa']
    evidence['comparison']=comparison
    (output/'audit.json').write_text(json.dumps(evidence,indent=2)+'\n')
    np.savez_compressed(output/'projection.npz',displacement=disp_image,tensile=stress_image,low=low,pixel=pixel)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(13,6),layout='constrained')
    extent=[low[0],low[0]+shape[0]*pixel,low[1],low[1]+shape[1]*pixel]
    for ax,values,title,units in zip(axes,[disp_image,stress_image],['Resultant displacement','Raw maximum principal stress'],['mm','MPa']):
        im=ax.imshow(values.T,origin='lower',extent=extent,cmap='inferno',vmin=0,interpolation='nearest')
        fig.colorbar(im,ax=ax,label=units,shrink=.8)
        ax.set(title=title,xlabel='X (mm)',ylabel='Y (mm)',aspect='equal')
    axes[0].plot(*p[imax,:2],marker='x',color='cyan',ms=8)
    axes[1].plot(*evidence['raw_tensile_peak']['position_mm'][:2],marker='x',color='cyan',ms=8)
    mesh_label=' x '.join(f'{v:g}' for v in spacing)
    fig.suptitle(f"{label}, {report['load_N']/9.81:.2f} kg | retained {mesh_label} mm sliced material, adaptive Q1\n"
                 'Maximum through width; E = 1 GPa planning model; mesh/material accuracy unqualified',fontsize=12)
    fig.savefig(output/'g-results.png',dpi=170)
    plt.close(fig)
    print(json.dumps(evidence,indent=2),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    for name in ['geometry','adaptive','result','output']:
        ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--compare',type=Path)
    ap.add_argument('--label',default='Rev G')
    args=ap.parse_args()
    audit(args.geometry,args.adaptive,args.result,args.output,args.compare,args.label)
