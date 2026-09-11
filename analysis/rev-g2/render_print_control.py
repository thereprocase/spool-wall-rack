"""Show the reinvested brace in actual credited Orca material sections."""
from pathlib import Path
import json
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shapely.geometry import shape, LineString
from plastic_shape import PlasticShape

D = Path(__file__).resolve().parent
ROOT = D.parents[1]
sys.path.insert(0, str(ROOT/'designs/rev-g2/shape-seeds'))
import generate as seeds


def main():
    names = ['ef-triangulated-asa-4w-1p6', 'ef-core-asa-4w-1p6']
    titles = ['Cut first / hollow diagonal', 'Reinvest / solid diagonal core']
    fig, axes = plt.subplots(1, 2, figsize=(12, 8), layout='constrained', facecolor='#f4f2ed')
    for ax, name, title in zip(axes, names, titles):
        cad = ROOT/'designs/rev-g2/print-controls'/name
        params = json.loads((cad/'selected-layout.json').read_text())
        outline = next(shape(v['geometry']) for v in json.loads((cad/'geometry.geojson').read_text())['features'] if v['properties']['name'] == 'hybrid_body_projection')
        material = PlasticShape.load(D/'.work/print-controls'/name/'shape')
        layer = next(raw for lo, hi, raw, _ in material.layers if lo <= 8.1 < hi)
        ax.set_facecolor('#f4f2ed')
        seeds.envelope.draw(ax, outline, '#dbe2df', edgecolor='#72837f')
        seeds.envelope.draw(ax, layer, '#337d80', edgecolor='none')
        if params.get('direct_brace_core'):
            brace = params['direct_brace']
            region = LineString(brace['points_XY_mm']).buffer(brace['radius_mm'], quad_segs=16)
            seeds.envelope.draw(ax, layer.intersection(region), '#c66536', edgecolor='none')
        seeds.draw_moulding(ax)
        receipt = json.loads((cad/'slice-verification.json').read_text())
        volume = receipt['comparison_with_matched_P1S_G']['all_print_moving_extrusion_volume_mm3']
        ax.set(aspect='equal', xlim=(-5, 216), ylim=(-66, 182), xlabel='Distance from wall / mm', ylabel='Height / mm',
               title=f"{title}\n{volume['EF']/1000:.2f} cm3 / {-volume['change_percent']:.2f}% below eight-wall G")
        ax.spines[['top', 'right']].set_visible(False)
    fig.suptitle('E + F / keep the skins, build a direct load path', fontsize=18, fontweight='bold')
    fig.supxlabel('Actual credited material at Z = 8.1 mm / ASA / four walls / 1.6 mm skins\nOrange: material inside the added core helper. Gray: body projection. Sacrificial bridges excluded.\nSliced geometry and material budget; mechanical and physical qualification are separate.', fontsize=11)
    out = ROOT/'designs/rev-g2/print-controls/reinvestment.png'
    fig.savefig(out, dpi=150); plt.close(fig)


if __name__ == '__main__':
    main()
