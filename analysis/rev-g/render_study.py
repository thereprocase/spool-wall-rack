"""Publication figures from the saved candidate ledger and complete 3D fields."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize

D = Path(__file__).resolve().parent
BG, INK, TEAL, GOLD, RED = '#f3f1e9', '#243d43', '#247a82', '#ba8428', '#b34032'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.labelcolor': INK, 'text.color': INK})


def frontier():
    summary = json.loads((D/'search-summary.json').read_text())
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), layout='constrained', facecolor=BG)
    records = []
    for run, color, label in zip(summary['runs'], [TEAL, '#748ca5', GOLD],
                                  ['Broad family / seed 1', 'Broad family / seed 2', 'Full planes / 3D feedback']):
        folder = D/'search-evidence'/run['search_signature'][:16]
        data = json.loads((D/'runs'/run['run']/'summary.json').read_text())
        rows = [json.loads((folder/f'candidate-{i}.json').read_text())
                for i in data['evaluated_candidate_ids']]
        rows = [r for r in rows if 'result' in r]
        records.extend(rows)
        axes[0].scatter([r['result']['nominal_mass_proxy_g_at_1p24'] for r in rows],
                        [r['result']['front_movement_mm_at_E1000'] for r in rows],
                        color=color, s=9, alpha=.28, edgecolors='none', label=label)
        ledger = json.loads((D/'runs'/run['run']/'generations.json').read_text())
        by_id = {r['id']: r for r in rows}
        axes[1].plot([r['generation'] for r in ledger],
                     [by_id[r['best_id']]['result']['nominal_mass_proxy_g_at_1p24'] for r in ledger],
                     color=color, lw=2, marker='.', label=label)
    axes[0].axhline(4, color=RED, lw=1, ls='--', label='4 mm bracket screen')
    axes[0].set(xlabel='Estimated plastic mass per bracket (g)', ylabel='2D front vertical movement (mm)',
                title='1,458 distinct parameter sets / coarse screen')
    axes[0].legend(fontsize=8, loc='upper right')
    axes[1].set(xlabel='Generation', ylabel='Best screen-feasible mass estimate (g)',
                title='Deterministic genetic progress')
    axes[1].legend(fontsize=8)
    for ax in axes:
        ax.set_facecolor(BG); ax.grid(alpha=.15)
    fig.suptitle('REV G / automated search, followed by independent acceptance checks', fontsize=17, fontweight='bold')
    fig.supxlabel('Mass in these panels is a quadrature proxy. These are 2D screens, not qualified designs.\nActual Orca mass and raw 3D failures are reported separately; matching E13 stiffness is not a constraint.', fontsize=10)
    fig.savefig(D/'search-frontier.png', dpi=180); plt.close(fig)


def refinement():
    rows = json.loads((D/'mechanics-summary.json').read_text())['fields']
    rows = sorted([r for r in rows if r['study'] == 'full-plane-best'], key=lambda r: -r['mesh_h_mm'])
    labels = [f"h = {r['mesh_h_mm']:g} mm\n{r['tetrahedra']:,} cells" for r in rows]
    x = np.arange(len(rows))
    fig, axes = plt.subplots(1, 3, figsize=(14, 5.2), layout='constrained', facecolor=BG)
    for ax in axes:
        ax.set_facecolor(BG); ax.grid(axis='y', alpha=.15); ax.set_xticks(x, labels); ax.set_xlim(-.3, 2.3)
    axes[0].plot(x, [r['front_vertical_movement_mm'] for r in rows], 'o-', color=TEAL, lw=2)
    axes[0].axhline(4, color=RED, ls='--', lw=1)
    axes[0].set(ylabel='Front vertical movement (mm)', ylim=(0, 4.4), title='Movement remains within planning screen')
    axes[1].plot(x, [r['raw_peak_tensile_MPa'] for r in rows], 'o-', color=RED, lw=2)
    axes[1].axhline(10.125, color=TEAL, ls='--', lw=1, label='40.5 MPa / 4')
    axes[1].set(ylabel='Raw maximum tensile principal stress (MPa)', ylim=(0, 62), title='Fracture screen fails at every mesh')
    axes[1].legend(fontsize=9)
    axes[2].plot(x, [r['material_volume_above_10p125MPa_mm3'] for r in rows], 'o-', color=GOLD, lw=2)
    axes[2].set(ylabel='Material volume above 10.125 MPa (mm³)', ylim=(0, .23), title='All finite overstressed cells retained')
    for i, row in enumerate(rows):
        axes[0].annotate(f"{row['front_vertical_movement_mm']:.3f}", (i, row['front_vertical_movement_mm']), xytext=(0, 8), textcoords='offset points', ha='center')
        axes[1].annotate(f"{row['raw_peak_tensile_MPa']:.2f}", (i, row['raw_peak_tensile_MPa']), xytext=(0, 8), textcoords='offset points', ha='center')
    fig.suptitle('REV G / full-plane finalist / 103.76 g actual sliced mass', fontsize=17, fontweight='bold')
    fig.supxlabel('12 kg reference load · E = 1 GPa · zero sparse-infill credit. Raw peaks increase and migrate with refinement.\nThis is not a converged rupture prediction and does not demonstrate the requested 4× fracture margin.', fontsize=10)
    fig.savefig(D/'stress-refinement.png', dpi=180); plt.close(fig)


def stress_sections():
    path = D/'studies/full-plane-best/print-material-1w-h1-solution.npz'
    with np.load(path, allow_pickle=False) as data:
        points, cells = data['p'], data['t']
        stress = np.linalg.eigvalsh(data['stress'].transpose(2, 0, 1))[:, 2]
    centers = points[cells].mean(1)
    hot = np.argmax(stress); xcut = centers[hot, 0]
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 6.2), layout='constrained', facecolor=BG)
    for ax in axes:
        ax.set_facecolor(BG)
    norm = Normalize(0, float(stress.max()))
    heat = axes[0].hexbin(centers[:, 0], centers[:, 1], C=stress, reduce_C_function=np.max,
                          gridsize=(140, 145), mincnt=1, cmap='inferno', norm=norm, linewidths=0)
    axes[0].scatter(*centers[hot, :2], marker='*', color='#39c6d2', edgecolor='white', s=125)
    axes[0].axvline(xcut, color=TEAL, ls='--', lw=.8)
    axes[0].set(aspect='equal', xlabel='Projection from wall X (mm)', ylabel='Installed height Y (mm)',
                title='Maximum raw stress through Z in each display bin')
    vertices = points[cells]
    cut_ids = np.flatnonzero((vertices[:, :, 0].min(1) < xcut) & (vertices[:, :, 0].max(1) > xcut))
    polygons, values = [], []
    edges = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
    for i in cut_ids:
        v = vertices[i]; hits = []
        for a, b in edges:
            if (v[a, 0]-xcut)*(v[b, 0]-xcut) < 0:
                t = (xcut-v[a, 0])/(v[b, 0]-v[a, 0]); hits.append((v[a]+t*(v[b]-v[a]))[[2, 1]])
        if len(hits) < 3:
            continue
        q = np.array(hits); c = q.mean(0); angle = np.arctan2(q[:, 1]-c[1], q[:, 0]-c[0])
        polygons.append(q[np.argsort(angle)]); values.append(stress[i])
    collection = PolyCollection(polygons, array=np.array(values), cmap='inferno', norm=norm, linewidth=0)
    axes[1].add_collection(collection); axes[1].autoscale()
    axes[1].set(aspect='equal', xlabel='Across printed width Z (mm)', ylabel='Installed height Y (mm)',
                title=f'Actual analysis-domain cut / X = {xcut:.3f} mm')
    axes[1].scatter(centers[hot, 2], centers[hot, 1], marker='*', color='#39c6d2', edgecolor='white', s=125)
    fig.colorbar(heat, ax=axes, label='Tensile principal stress (MPa)', shrink=.75)
    fig.suptitle('REV G / the fine-mesh hotspot reaches the preserved forearm chamfer', fontsize=16, fontweight='bold')
    fig.supxlabel('Complete h1 finite-cell stress field. Left: maximum projection for display; right: true tetrahedron/plane intersections.\nColor range includes the raw maximum. The star marks its location; no cells are removed from the mechanical assessment.', fontsize=10)
    fig.savefig(D/'stress-sections.png', dpi=190); plt.close(fig)


if __name__ == '__main__':
    frontier(); refinement(); stress_sections()
    print('Search, refinement and actual 3D stress-section figures rendered')
