"""Render the actual delivered body mesh, without changing its geometry."""
from pathlib import Path
import importlib.util
import numpy as np
import matplotlib
matplotlib.use('Agg')
from PIL import Image, ImageDraw, ImageFont

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
spec = importlib.util.spec_from_file_location('g_render', ROOT/'designs/rev-g/render_cpu.py')
shared = importlib.util.module_from_spec(spec); spec.loader.exec_module(shared)


def main():
    data = (D/'body-only.stl').read_bytes()
    count = int.from_bytes(data[80:84], 'little')
    dtype = np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')])
    assert len(data) == 84+50*count
    vv = np.frombuffer(data,offset=84,dtype=dtype,count=count)['vertices'].astype(float)
    vv[:,:,0] = 250-vv[:,:,0]; vv[:,:,1] = 182-vv[:,:,1]
    vv = vv[:,:,[0,2,1]]; vv[:,:,1] *= -1
    colors = shared.shade(vv, (.23,.52,.54))
    width, height = 1600, 1450
    elevation, azimuth = np.radians([17,-57])
    eye = np.array([np.cos(elevation)*np.cos(azimuth),np.cos(elevation)*np.sin(azimuth),np.sin(elevation)])
    right = np.array([-np.sin(azimuth),np.cos(azimuth),0]); up = np.cross(eye,right)
    xyz = vv @ np.array([right,up,eye]).T
    low = xyz[:,:,:2].min(axis=(0,1)); high = xyz[:,:,:2].max(axis=(0,1))
    scale = min((width-200)/(high[0]-low[0]),(height-300)/(high[1]-low[1]))
    xyz[:,:,0] = (xyz[:,:,0]-(low[0]+high[0])/2)*scale+width/2
    xyz[:,:,1] = -(xyz[:,:,1]-(low[1]+high[1])/2)*scale+height/2+30
    depth_buffer = np.full((height,width),-np.inf)
    pixels = np.full((height,width,3),[243,241,233],dtype=np.uint8)
    for triangle, color in zip(xyz, colors):
        x0=max(0,int(np.floor(triangle[:,0].min()))); x1=min(width-1,int(np.ceil(triangle[:,0].max())))
        y0=max(0,int(np.floor(triangle[:,1].min()))); y1=min(height-1,int(np.ceil(triangle[:,1].max())))
        if x0>x1 or y0>y1: continue
        a,b,c=triangle
        denominator=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(denominator)<1e-8: continue
        xx,yy=np.meshgrid(np.arange(x0,x1+1)+.5,np.arange(y0,y1+1)+.5)
        u=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/denominator
        v=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/denominator; w=1-u-v
        depth=u*a[2]+v*b[2]+w*c[2]; old=depth_buffer[y0:y1+1,x0:x1+1]
        mask=(u>=-1e-8)&(v>=-1e-8)&(w>=-1e-8)&(depth>old)
        old[mask]=depth[mask]; pixels[y0:y1+1,x0:x1+1][mask]=np.uint8(color*255)
    im=Image.fromarray(pixels); draw=ImageDraw.Draw(im)
    fonts=Path(matplotlib.get_data_path())/'fonts/ttf'
    draw.rectangle((0,0,width,145),fill='#f3f1e9')
    draw.text((70,48),'E + F / UPPER MAST TRIM',font=ImageFont.truetype(str(fonts/'DejaVuSans-Bold.ttf'),31),fill='#243d43')
    draw.text((70,102),'Actual CAD / 6 mm mast web, tapered shoulders, unchanged rod and mount regions',font=ImageFont.truetype(str(fonts/'DejaVuSans.ttf'),21),fill='#667779')
    draw.rectangle((0,height-65,width,height),fill='#f3f1e9')
    draw.text((70,height-44),'PROTOTYPE CAD / ALIGNED 100% INFILL HELPERS SUPPLIED SEPARATELY / NOT A LOAD RATING',font=ImageFont.truetype(str(fonts/'DejaVuSans.ttf'),16),fill='#667779')
    im.save(D/'progress-exterior.png')
    print('Actual CAD triangles rendered:',count,flush=True)


if __name__ == '__main__': main()
