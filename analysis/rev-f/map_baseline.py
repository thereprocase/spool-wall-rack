"""Map the actual E13 in-plane strain-energy density to guide Rev F windows."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
D=Path(__file__).resolve().parent
root=D.parents[1]
data=np.load(D.parent/'e13/e13-8w-h1-full-solution.npz')
p,t,sig,vol,th=(data[k] for k in ['p','t','stress','volume','thickness'])
nu=.35;E=1000
energy=(sig[0,0]**2+sig[1,1]**2-2*nu*sig[0,0]*sig[1,1]+2*(1+nu)*sig[0,1]**2)/(2*E)
fig,axes=plt.subplots(1,2,figsize=(13,8),layout='constrained')
for ax,field,title,cap,cmap in [(axes[0],energy,'Elastic strain-energy density / E13',.008,'magma'),(axes[1],th,'Effective printed thickness / E13',24,'viridis')]:
    pc=PolyCollection(p[t],array=field,cmap=cmap,edgecolors='none');pc.set_clim(0,cap);ax.add_collection(pc)
    ax.set(xlim=(-5,212),ylim=(-48,180),aspect='equal',title=title,xlabel='Projection X / mm',ylabel='Height Y / mm')
    ax.grid(alpha=.15);fig.colorbar(pc,ax=ax,shrink=.65)
fig.suptitle('Rev F starting point / place voids in low-energy material',fontsize=17)
fig.savefig(D/'baseline-energy-map.png',dpi=160)
print({'elements':len(t),'volume_mm3':float(vol.sum()),'strain_energy_Nmm':float((energy*vol).sum())})
