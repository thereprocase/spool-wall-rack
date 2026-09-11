"""Compare parameter-defined helpers on the verified EF body projection."""
from pathlib import Path
import argparse,json,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shapely.geometry import shape,LineString
from shapely import union_all
D=Path(__file__).resolve().parent;ROOT=D.parents[1]
sys.path.insert(0,str(ROOT/'designs/rev-g'))
import layout
sys.path.insert(0,str(ROOT/'designs/rev-g2/shape-seeds'))
import generate as seeds


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('candidates',nargs='+');args=ap.parse_args()
    fig,axes=plt.subplots(1,len(args.candidates),figsize=(6*len(args.candidates),7),layout='constrained',squeeze=False)
    for ax,name in zip(axes[0],args.candidates):
        folder=ROOT/'designs/rev-g2'/name;p=json.loads((folder/'selected-layout.json').read_text())
        outline=next(shape(v['geometry']) for v in json.loads((folder/'geometry.geojson').read_text())['features'] if v['properties']['name']=='hybrid_body_projection')
        seeds.envelope.draw(ax,outline,'#dce4e3',edgecolor='#506365')
        dense=layout.dense_at_z(outline,p,12.1)
        seeds.envelope.draw(ax,dense,'#c39b44',edgecolor='none')
        if p.get('local_reinforcement'):
            if 'radii_mm' in p['local_reinforcement'][0]:
                import importlib.util
                spec=importlib.util.spec_from_file_location('tapered_helper',folder/'reinforcement.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
                extra=union_all(module.tapered_regions(p)).intersection(outline)
            else:
                extra=union_all([LineString(v['points_XY_mm']).buffer(v['radius_mm'],quad_segs=12) for v in p['local_reinforcement']]).intersection(outline)
            seeds.envelope.draw(ax,extra,'#bd4936',edgecolor='none')
        seeds.draw_moulding(ax)
        verification=folder/'slice-verification.json'
        saving='slice pending'
        if verification.exists():
            r=json.loads(verification.read_text());change=r['comparison_with_matched_P1S_G']['all_print_moving_extrusion_volume_mm3']['change_percent'];saving=f'{-change:.2f}% less spent plastic than G'
        ax.set(aspect='equal',xlim=(-5,215),ylim=(-66,182),xlabel='Distance from wall / mm',ylabel='Height / mm',title=name+'\n'+saving)
        ax.spines[['top','right']].set_visible(False)
    fig.suptitle('E + F / cut first, then place material at the transitions',fontsize=19,fontweight='bold')
    fig.supxlabel('Gray: body projection   Gold: background dense helper   Red: local reinforcement helper\nHelper footprint illustration, not a toolpath or strength result. Skins and the central plate are recorded separately; holes still cut the solid.',fontsize=11)
    args.output.parent.mkdir(parents=True,exist_ok=True);fig.savefig(args.output,dpi=160);plt.close(fig)

if __name__=='__main__':main()
