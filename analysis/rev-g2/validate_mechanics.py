"""Manufactured numerical checks for the Rev-G2 mechanics assumptions.

This does not invoke the full mesh/contact solve.  It exercises the same
scikit-fem linear-elasticity kernel and an independently specified one-DOF
unilateral contact problem, so it catches constitutive/DOF mistakes that a
small global residual cannot detect.
"""
from pathlib import Path
import argparse, json
import numpy as np
from scipy.sparse import csr_matrix
from skfem import MeshTet, Basis, ElementTetP1, ElementVector, asm
from skfem.models.elasticity import linear_elasticity


def elastic_fixture():
    p = np.array([[0., 1., 0., 0.], [0., 0., 1., 0.], [0., 0., 0., 1.]])
    t = np.array([[0], [1], [2], [3]])
    mesh = MeshTet(p, t)
    basis = Basis(mesh, ElementVector(ElementTetP1()))
    E, nu = 1000., .35
    mu = E/(2*(1+nu)); lam = E*nu/((1+nu)*(1-2*nu))
    # Nontrivial affine displacement: symmetric strain plus translation.
    A = np.array([[.010, .003, -.002], [.003, -.004, .001], [-.002, .001, .006]])
    b = np.array([.7, -.2, .4])
    U = (A @ p + b[:, None]).T
    u = U.reshape(-1)
    K = asm(linear_elasticity(lam, mu), basis)
    eps = (A+A.T)/2
    sigma = 2*mu*eps + lam*np.trace(eps)*np.eye(3)
    volume = float(basis.dx.sum())
    analytic_energy = .5*volume*float(np.sum(sigma*eps))
    assembled_energy = .5*float(u @ (K @ u))
    # skfem gradient is (component, spatial derivative, element, quadrature).
    recovered = basis.interpolate(u).grad.mean(axis=(2, 3))
    recovered_eps = (recovered + recovered.T)/2
    recovered_sigma = 2*mu*recovered_eps + lam*np.trace(recovered_eps)*np.eye(3)
    stress_error = float(np.max(np.abs(recovered_sigma-sigma)))
    # Rigid modes must have no strain energy (translation and infinitesimal rotation).
    translation = np.tile(np.array([.2, -.4, .1]), (4, 1)).reshape(-1)
    W = np.array([[0., -.3, .2], [.3, 0., -.1], [-.2, .1, 0.]])
    rotation = (W @ p).T.reshape(-1)
    translation_energy = .5*float(translation @ (K @ translation))
    rotation_energy = .5*float(rotation @ (K @ rotation))
    assert stress_error < 1e-10
    assert abs(assembled_energy-analytic_energy) < 1e-10
    assert abs(translation_energy) < 1e-12 and abs(rotation_energy) < 1e-12
    return {"tetra_volume_mm3":volume, "E_MPa":E, "nu":nu,
            "analytic_energy_Nmm":analytic_energy, "assembled_energy_Nmm":assembled_energy,
            "max_recovered_stress_error_MPa":stress_error,
            "translation_energy_Nmm":translation_energy, "rotation_energy_Nmm":rotation_energy,
            "status":"pass"}


def contact_fixture():
    # Two-node, 3-DOF/node spring.  Node 0 is fixed; node 1 contacts x=0.
    # The production PDAS loop is called below; answers are independent.
    from solve_plastic import solve_contact
    k, gap0 = 10., .2
    K = np.zeros((6, 6)); K[0,0] = K[3,3] = k; K[0,3] = K[3,0] = -k
    K[1,1] = K[2,2] = K[4,4] = K[5,5] = k
    K = csr_matrix(K)
    base = np.array([0, 1, 2, 4, 5]); wall = np.array([1])
    cases = []
    for name, force, initial_gap in [("open", -1., gap0), ("closed", -5., gap0),
                                     ("touching_closed", -1., 0.),
                                     ("release_zero_gap", 2., 0.),
                                     ("exactly_touching", -2., gap0)]:
        f = np.zeros(6); f[3] = force
        uvec, rvec, free, active, gaps, iterations = solve_contact(
            K, f, base, wall, np.array([initial_gap]), solver='superlu')
        u, reaction = float(uvec[3]), float(rvec[3])
        free_u = force/k
        if initial_gap+free_u >= 0:
            expected_u, expected_reaction = free_u, 0.
        else:
            expected_u, expected_reaction = -initial_gap, k*(-initial_gap)-force
        gap = initial_gap+u
        residual = k*u-force-reaction
        cases.append({"case":name,"force_N":force,"displacement_mm":u,
                      "initial_gap_mm":initial_gap,"expected_displacement_mm":expected_u,
                      "expected_reaction_N":expected_reaction,"gap_mm":gap,"reaction_N":reaction,
                      "equilibrium_residual_N":residual,"active_nodes":active.tolist(),
                      "iterations":iterations})
        assert abs(u-expected_u) < 1e-12 and abs(reaction-expected_reaction) < 1e-12
        assert gap >= -1e-12 and reaction >= -1e-12 and abs(gap*reaction) < 1e-12
        assert abs(residual) < 1e-12
    assert cases[0]["reaction_N"] == 0 and cases[1]["reaction_N"] > 0
    assert cases[3]["active_nodes"] == []
    return {"spring_k_N_per_mm":k,"initial_gap_mm":gap0,"cases":cases,
            "complementarity":"gap >= 0, reaction >= 0, gap*reaction = 0", "status":"pass"}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--output",type=Path,default=Path("analysis/rev-g2/validation/mechanics-fixtures.json")); args=ap.parse_args()
    report={"elastic_affine_tetra":elastic_fixture(),"unilateral_contact":contact_fixture(),
            "scope":"Manufactured constitutive and contact-kernel assumptions only; full 3D mesh solve, patch classification, and physical strength remain separate.",
            "status":"PASS"}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__ == "__main__": main()
