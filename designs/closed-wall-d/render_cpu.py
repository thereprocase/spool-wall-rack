from pathlib import Path
import re,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
D=Path(__file__).resolve().parent
bg='#f3f1e9'

def read_stl(name,printed=False):
 s=(D/name).read_text()
 v=np.array([list(map(float,p)) for p in re.findall(r'vertex\s+(\S+)\s+(\S+)\s+(\S+)',s)]).reshape(-1,3,3)
 if printed:v[:,:,0]=250-v[:,:,0];v[:,:,1]=156-v[:,:,1]
 # Mount coordinates: X from wall, Y along rack, Z upward.
 v=v[:,:,[0,2,1]];v[:,:,1]*=-1
 return v

def cyl(x,y,z,r,length,n=96):
 angles=np.linspace(0,2*np.pi,n,endpoint=False);p=np.c_[x+r*np.cos(angles),np.full(n,y-length/2),z+r*np.sin(angles)];q=p.copy();q[:,1]=y+length/2
 v=[]
 for i in range(n):
  j=(i+1)%n;v.extend([[p[i],p[j],q[j]],[p[i],q[j],q[i]],[[x,y-length/2,z],p[j],p[i]],[[x,y+length/2,z],q[i],q[j]]])
 return np.array(v)

def shade(v,base):
 norm=np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0]);norm/=np.maximum(np.linalg.norm(norm,axis=1)[:,None],1e-12)
 lights=[np.array([-.5,-.75,1]),np.array([.7,.2,.4])]
 intensity=np.full(len(v),.42)
 for l,w in zip(lights,[.43,.15]):
  l=l/np.linalg.norm(l);intensity+=w*np.maximum(0,norm@l)
 col=np.asarray(base)
 if col.ndim==1:col=np.tile(col,(len(v),1))
 return np.clip(col*intensity[:,None],0,1)

def render(name,parts,title,subtitle,view=(19,-59),lim=None,dims=None):
 from PIL import Image,ImageDraw,ImageFont
 W,H=1800,1500
 vv=np.concatenate([v for v,c in parts]);cc=np.concatenate([shade(v,c) for v,c in parts])
 el,az=np.radians(view)
 eye=np.array([np.cos(el)*np.cos(az),np.cos(el)*np.sin(az),np.sin(el)])
 right=np.array([-np.sin(az),np.cos(az),0]);up=np.cross(eye,right)
 xyz=vv@np.array([right,up,eye]).T
 lo=xyz[:,:,:2].min(axis=(0,1));hi=xyz[:,:,:2].max(axis=(0,1))
 scale=min((W-230)/(hi[0]-lo[0]),(H-340)/(hi[1]-lo[1]))
 xyz[:,:,0]=(xyz[:,:,0]-(lo[0]+hi[0])/2)*scale+W/2
 xyz[:,:,1]=-(xyz[:,:,1]-(lo[1]+hi[1])/2)*scale+H/2+30
 buf=np.full((H,W),-np.inf);rgb=np.full((H,W,3),[243,241,233],dtype=np.uint8)
 for tri,col in zip(xyz,cc):
  x0=max(0,int(np.floor(tri[:,0].min())));x1=min(W-1,int(np.ceil(tri[:,0].max())))
  y0=max(0,int(np.floor(tri[:,1].min())));y1=min(H-1,int(np.ceil(tri[:,1].max())))
  if x0>x1 or y0>y1:continue
  p,q,r=tri;den=(q[1]-r[1])*(p[0]-r[0])+(r[0]-q[0])*(p[1]-r[1])
  if abs(den)<1e-8:continue
  xx,yy=np.meshgrid(np.arange(x0,x1+1)+.5,np.arange(y0,y1+1)+.5)
  u=((q[1]-r[1])*(xx-r[0])+(r[0]-q[0])*(yy-r[1]))/den
  v=((r[1]-p[1])*(xx-r[0])+(p[0]-r[0])*(yy-r[1]))/den;w=1-u-v
  depth=u*p[2]+v*q[2]+w*r[2];region=buf[y0:y1+1,x0:x1+1]
  mask=(u>=-1e-8)&(v>=-1e-8)&(w>=-1e-8)&(depth>region)
  region[mask]=depth[mask];rgb[y0:y1+1,x0:x1+1][mask]=np.uint8(col*255)
 im=Image.fromarray(rgb);draw=ImageDraw.Draw(im)
 fonts='/usr/share/fonts/truetype/dejavu/'
 draw.text((90,65),title,font=ImageFont.truetype(fonts+'DejaVuSans-Bold.ttf',34),fill='#243d43')
 draw.text((90,121),subtitle,font=ImageFont.truetype(fonts+'DejaVuSans.ttf',22),fill='#667779')
 draw.text((90,H-70),'REV D · ACTUAL CAD GEOMETRY · PROGRESS RENDER',font=ImageFont.truetype(fonts+'DejaVuSans.ttf',17),fill='#667779')
 im.save(D/name)

body=read_stl('bracket.stl',True)
parts=[(body,(.23,.52,.54))]
for x in [76,226]:parts.append((cyl(x,-12,-.3,12.7,180),(.83,.67,.44)))
render('progress-exterior.png',parts,'CLOSED-WALL BRACKET','Upward wall leg · continuous closed faces · exposed dowel bearing surfaces')
print('Exterior rendered')
if (D/'arm-section.stl').exists():
 v=read_stl('arm-section.stl')
 # Warm cut faces show the cross-section without changing geometry.
 cols=np.tile([.23,.52,.54],(len(v),1))
 cut=np.ptp(v[:,:,0],axis=1)<.001;cut &= np.abs(v[:,:,0].mean(1)-125)<.01
 cols[cut]=[.97,.66,.28]
 render('progress-cutaway.png',[(v,cols)],'CUT THROUGH THE ARM','Three hollow volumes · two internal plates · two outer faces',view=(21,-38),lim=((0,130),(-40,16),(-95,160)),dims=(130,56,255))
 print('Cutaway rendered')
if (D/'exploded-plates.stl').exists():
 v=read_stl('exploded-plates.stl');original_y=v[:,:,1].copy()
 group=np.rint(-v[:,:,1].mean(1)/14).astype(int)
 # Increase spacing only for this explicitly exploded explanation.
 for i in range(4):v[group==i,:,1]-=i*23
 cols=np.tile([.23,.52,.54],(len(v),1));cols[np.isin(group,[1,2])]=[.97,.66,.28]
 render('progress-plates.png',[(v,cols)],'CONTINUOUS INTERNAL PLATES','Exploded explanation · each full L-shaped plate is 1.2 mm thick',view=(19,-49),lim=((0,245),(-116,2),(-95,160)),dims=(245,118,255))
 print('Exploded plates rendered')
