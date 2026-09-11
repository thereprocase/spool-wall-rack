"""Second search family after the thin shaped-plane finalist failed 3D gates.

Full planes and stronger local support are a bounded response to the observed
3D failure mechanism, not a replacement for the unchanged final strength gate.
"""
from pathlib import Path
import argparse
import hashlib
import json
import search

search.GENES.update({
    'walls': [1, 2, 3, 4],
    'skin_mm': [1., 1.2],
    'plane_mm': [1., 1.2],
    'planes': ['full'],
    'bottom_band': [round(x/5, 1) for x in range(8, 31)],
    'diagonal_band': [round(x/5, 1) for x in range(8, 31)],
    'seat_band': [x/2 for x in range(10, 21)],
    'front_seat_band': [2., 2.5, 3., 3.5, 4.],
    'rib_frame': [4.],
    'lower_tunnel_collar_mm': [3.5, 4., 4.5, 5.],
    'upper_tunnel_collar_mm': [2.5, 3., 3.5, 4.],
})
search.LIMITS.update({'front_movement_mm_at_E1000': 3.6, 'raw_peak_tensile_MPa': 7.0})

# Project the inherited shaped-plane seed into this full-plane family.
# Include this entrypoint's exact source in the cache/search signature.
original_encode = search.encode
original_signature = search.search_signature
def encode(params):
    projected = dict(params)
    for key, choices in search.GENES.items():
        if isinstance(choices[0], str) and projected.get(key) not in choices:
            projected[key] = choices[0]
    return original_encode(projected)
def signature(h):
    return hashlib.sha256((original_signature(h)+Path(__file__).read_text(encoding='utf-8')).encode()).hexdigest()
search.encode = encode
search.search_signature = signature


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=20260912)
    parser.add_argument('--tag', default='3d-feedback-seed-20260912')
    args = parser.parse_args()
    summary = search.run(args.seed, 24, 14, 2., tag=args.tag)
    rationale = {
        'trigger_candidate': '82e88fcf29749880c5c3',
        'trigger_2D_fine_front_mm': 4.0012347103150345,
        'trigger_3D_h2_front_mm': 4.929884100935147,
        'trigger_3D_h2_raw_peak_tensile_MPa': 120.46400337752169,
        'changed_search_family': 'Full internal planes; thicker skins and local tunnel/seat support; additional 2D screening reserve.',
        'final_3D_strength_limit_MPa_unchanged': 10.125,
        'final_bracket_movement_limit_mm_unchanged': 4.,
        'new_genes': search.GENES, 'new_screen_limits': search.LIMITS,
        'search_signature': summary['search_signature'],
        'note': 'This bounded second family does not prove all shaped-plane designs infeasible. Actual slicing and 3D gates remain required.'}
    (search.D/'3d-feedback-search.json').write_text(json.dumps(rationale, indent=2)+'\n')
