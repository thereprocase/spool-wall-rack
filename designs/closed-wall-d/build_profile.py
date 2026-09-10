from pathlib import Path
import numpy as np
D=Path(__file__).resolve().parent
p=[]
def line(pt):p.append(np.array(pt,dtype=float))
def bez(c1,c2,end,n=32):
 a=p[-1].copy(); b=np.array(c1); c=np.array(c2); d=np.array(end)
 for t in np.linspace(0,1,n+1)[1:]:p.append((1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d)
line((0,150));line((0,-42))
bez((0,-75),(12,-90),(42,-90))
bez((103,-87),(174,-64),(226,-48))
bez((239,-44),(240,-30),(226,-30))
line((92,-30))
bez((72,-30),(66,-23),(61,-6))
line((24,114))
bez((20,127),(20,139),(20,150))
(D/'profile_points.scad').write_text('profile_points='+str(np.round(p,5).tolist())+';\n')
