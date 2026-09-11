"""Publishable mesh and convergence figure from retained numerical evidence."""
from pathlib import Path
import argparse
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--adaptive',type=Path,required=True)
    ap.add_argument('--fixtures',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args = ap.parse_args()
    report = json.loads((args.adaptive/'adaptive.json').read_text())
    fixtures = json.loads((args.fixtures/'fixtures.json').read_text())
    with np.load(args.adaptive/'adaptive.npz') as data:
        cells,scale = data['cells'],data['scale']
    spacing,origin = np.array(report['spacing_mm']),np.array(report['origin_mm'])
    z = 12.1
    keep = (cells[:,2]*spacing[2]+origin[2] <= z)&((cells[:,2]+scale)*spacing[2]+origin[2] > z)
    xy = cells[keep,:2]*spacing[:2]+origin[:2]
    wh = scale[keep,None]*spacing[:2]
    corners = np.array([[0,0],[1,0],[1,1],[0,1]])
    boxes = xy[:,None,:]+corners[None]*wh[:,None,:]
    colors = np.where(scale[keep] == 1,'#12759d','#efa044')
    fig,axes = plt.subplots(1,3,figsize=(14,5),gridspec_kw={'width_ratios':[1.05,1.,1.2]},layout='constrained')
    for ax in axes[:2]:
        ax.add_collection(PolyCollection(boxes,facecolors=colors,edgecolors='#283b45',linewidths=.12))
        ax.set_aspect('equal')
        ax.set_xlabel('Installed X, mm')
        ax.set_ylabel('Installed Y, mm')
    axes[0].set_xlim(-5,213)
    axes[0].set_ylim(-49,182)
    axes[0].set_title('Rev G adaptive section, Z = 12.1 mm')
    axes[0].legend(handles=[Patch(color='#12759d',label='0.2 mm elements'),Patch(color='#efa044',label='0.4 mm elements')],loc='upper right',fontsize=8)
    axes[1].set_xlim(35,51)
    axes[1].set_ylim(-14,2)
    axes[1].set_title('Same mesh: local detail')
    rows = fixtures['thin_beam_refinement']
    reference = rows[-1]['compliance_Nmm']
    x = [r['cells'] for r in rows]
    y = [100*(1-r['compliance_Nmm']/reference) for r in rows]
    axes[2].plot(x,y,'o-',color='#12759d')
    axes[2].set_xlabel('Retained beam elements')
    axes[2].set_ylabel('Movement shortfall vs uniform fine mesh, %')
    axes[2].set_title('Independent thin-beam refinement')
    axes[2].grid(alpha=.2)
    axes[2].set_ylim(-.5,11.5)
    axes[2].set_xlim(80,1140)
    for xx,yy in zip(x,y):
        axes[2].annotate(f'{yy:.2f}%',(xx,yy),xytext=(5,7),textcoords='offset points',fontsize=8)
    fig.suptitle(f"Adaptive mesh: {report['fine_cells']:,} → {report['leaf_cells']:,} cells; same voxel material",fontsize=15)
    fig.supxlabel('Seats, fixings, wall contact and split-bond neighborhoods stay fine. The source 0.2 mm voxel union still omits 8.02% of raw nominal plastic.\nMesh/fixture evidence only; whole-G load convergence and physical qualification are separate.',fontsize=9)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(args.output,dpi=170)
    plt.close(fig)


if __name__ == '__main__':
    main()
