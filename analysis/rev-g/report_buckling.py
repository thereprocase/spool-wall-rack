"""Render saved quadratic modes and publish their bounded interpretation."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

D = Path(__file__).resolve().parent


def main():
    cases = [('repaired-f-light', 'Preserved F light design'),
             ('full-plane-best', 'G full-plane feedback finalist')]
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 6.5), layout='constrained', facecolor='#f3f1e9')
    records = []
    for ax, (folder, title) in zip(axes, cases):
        prefix = D/'studies'/folder/'buckling-p2-h2'
        result = json.loads(prefix.with_suffix('.json').read_text())
        assert all(r['relative_eigen_residual'] < 1e-5 for r in result['modes'])
        with np.load(prefix.with_suffix('.npz'), allow_pickle=False) as data:
            p = data['mode_nodes']; amplitude = np.linalg.norm(data['modes'][:, :, 0], axis=1)
        assert np.all(np.isfinite(amplitude)) and abs(amplitude.max()-1) < 1e-10
        plot = ax.hexbin(p[:, 0], p[:, 1], C=amplitude, reduce_C_function=np.max,
                        gridsize=(110, 120), mincnt=1, cmap='viridis', vmin=0, vmax=1, linewidths=0)
        ax.set(aspect='equal', xlabel='Projection X (mm)', ylabel='Installed height Y (mm)',
               title=f"{title}\nFirst linear multiplier = {result['lowest_positive_multiplier']:.3f}", facecolor='#f3f1e9')
        ax.spines[['top', 'right']].set_visible(False)
        records.append(result)
    fig.colorbar(plot, ax=axes, label='Relative first-mode amplitude / maximum = 1', shrink=.75)
    fig.suptitle('REV G / quadratic linear-buckling mode localization', fontsize=17, fontweight='bold', color='#243d43')
    fig.supxlabel('All quadratic mode nodes projected through the 24 mm width; each display bin shows its maximum amplitude.\nEigenmode amplitude is arbitrary, not a predicted displacement. Fixed contact, isotropy and conservative load direction apply.', fontsize=10)
    fig.savefig(D/'buckling-modes.png', dpi=180); plt.close(fig)
    p1 = json.loads((D/'studies/repaired-f-light/buckling-p1-h2.json').read_text())
    value = records[1]['lowest_positive_multiplier']
    text = f'''# Rev G — linear buckling screen

The full-plane G candidate has a first positive quadratic linear-buckling
multiplier of **{value:.4f}** relative to the 12 kg reference load at
E = 1 GPa. The preserved F light candidate gives **{records[0]['lowest_positive_multiplier']:.4f}**.
Both exceed one in this model. These are linear bifurcation multipliers,
not physical safe-load factors or the requested fracture margin. Both
designs remain rejected by their raw tensile-principal-stress screen.

![Complete quadratic mode localization](buckling-modes.png)

## Formulation and benchmark

[buckling.py](buckling.py) solves `(K + lambda Kg) phi = 0` using
the complete saved constant-strain tetrahedral prestress. The geometric
form is the volume integral of `sigma_ij v_k,i u_k,j`. It solves the
equivalent inverse-load eigenproblem with the elastic matrix as the
positive-definite metric. Diagonal congruence scaling and residual-corrected
factor solves improve numerical accuracy without changing material.

The quadratic displacement basis uses degree-two integration, exact for
products of its affine-tetrahedron gradients with cellwise constant prestress.
All finite prestress cells are retained. The converged wall-contact set is
held fixed; washer/bore constraints follow the static model. Quadratic wall
nodes inherit the nearest static wall-node contact state.

A 20 × 1 × 1 mm simply supported beam at E = 1,000 MPa, nu = 0 and unit
axial compression has an Euler reference of 2.05617 N. First-order models
overpredict it by 14.77%, 6.19% and 3.18% as their mesh is refined. The
quadratic model is within 0.69%; the small difference includes continuum
shear compliance. [Benchmark and residuals](buckling-validation.json).

The actual F light design changes from **{p1['lowest_positive_multiplier']:.4f} with P1**
to **{records[0]['lowest_positive_multiplier']:.4f} with P2** on the same tetrahedral geometry
and prestress. That large difference is why the P1 rack value is not used
as the reported stability result. The benchmark establishes the formulation
and exposes locking; it does not establish whole-rack mesh convergence.

## Saved complete results

| Design and order | Eigenvalues/residuals | All mode nodes and vectors |
|---|---|---|
| F light, P1 | [JSON](studies/repaired-f-light/buckling-p1-h2.json) | [NPZ](studies/repaired-f-light/buckling-p1-h2.npz) |
| F light, P2 | [JSON](studies/repaired-f-light/buckling-p2-h2.json) | [NPZ](studies/repaired-f-light/buckling-p2-h2.npz) |
| G full planes, P2 | [JSON](studies/full-plane-best/buckling-p2-h2.json) | [NPZ](studies/full-plane-best/buckling-p2-h2.npz) |

Every recorded physical eigenpair residual is below 10⁻⁵. The G factor
has about 1.25 million free degrees of freedom and 86.9 million nonzeros;
the recorded solve takes about 10.5 minutes on the reference workstation.
Source field hashes tie the prestress to the preserved static solutions.

## Limits

This is one quadratic whole-rack mesh level with h2 static prestress. It
does not prove a converged nonlinear buckling load. Geometric imperfections,
orthotropic printed behavior, contact-set changes, load-direction changes,
creep evolution and postbuckling are not resolved. The mode images show
arbitrary normalized eigenvectors, not deflection under service load.

The derivation follows the primary
[3D solid buckling formulation](https://bleyerj.github.io/comet-fenicsx/tours/eigenvalue_problems/buckling_3d_solid/buckling_3d_solid.html).
The implementation uses the documented
[SciPy symmetric generalized eigensolver](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html)
and [scikit-fem finite-element API](https://scikit-fem.readthedocs.io/en/stable/api.html).

[Return to the mechanical study](README.md).
'''
    (D/'BUCKLING.md').write_text(text, encoding='utf-8')
    print('Quadratic mode render and bounded buckling report complete')


if __name__ == '__main__':
    main()
