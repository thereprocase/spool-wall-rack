// Reproduce the raised-front clearance check using only Node.js standard library.
// This checks the UNMODIFIED E8 profile, not a redesigned raised-front bracket.
const fs = require('node:fs');
const path = require('node:path');
const svg = fs.readFileSync(path.join(__dirname, '../../designs/closed-wall-e8/profile.svg'), 'utf8');
const outline = svg.match(/<path[^>]*d="([^"]+)"/)[1];
const points = [...outline.matchAll(/([-+\d.eE]+),([-+\d.eE]+)/g)].map(m => [+m[1], -m[2]]);
function nearest(center) {
  let best = { distance: Infinity };
  for (let i = 0; i < points.length; i++) {
    const a = points[i], b = points[(i+1) % points.length];
    const v = [b[0]-a[0], b[1]-a[1]], length2 = v[0]**2 + v[1]**2;
    if (!length2) continue;
    const u = Math.max(0, Math.min(1, ((center[0]-a[0])*v[0] + (center[1]-a[1])*v[1]) / length2));
    const q = [a[0]+u*v[0], a[1]+u*v[1]];
    const distance = Math.hypot(q[0]-center[0], q[1]-center[1]);
    if (distance < best.distance) best = {distance, point:q};
  }
  return best;
}
const results = [];
for (const diameter of [180, 200, 220]) for (const frontRise of [0, 12]) {
  const spacing = Math.hypot(100, frontRise);
  const q = Math.sqrt((diameter/2+12.7)**2-spacing**2/4);
  const center = [140-frontRise*q/spacing, frontRise/2+100*q/spacing];
  const n = nearest(center);
  results.push({diameter,frontRise,center,clearance:n.distance-diameter/2,nearest:n.point});
}
console.log(JSON.stringify({vertices:points.length,results},null,2));
