"""Seeded integer genetic search; cached numerical screens, never a load rating."""
from pathlib import Path
import argparse
import hashlib
import json
import time
import importlib.metadata
import numpy as np
from fast_screen import Screen, D, ROOT, source_hash

# Every gene maps to a finite manufacturing choice. Continuous millimeter
# values below are quantized before evaluation, so cache keys are unambiguous.
GENES = {
    'walls': list(range(1, 9)),
    'skin_mm': [.6, .8, 1., 1.2],
    'plane_mm': [.6, .8, 1., 1.2],
    'planes': ['full', 'shaped'],
    'bottom_band': [round(x/5, 1) for x in range(6, 41)],
    'diagonal_band': [round(x/5, 1) for x in range(6, 41)],
    'seat_band': [x/2 for x in range(5, 27)],
    'front_seat_band': [x/2 for x in range(4, 11)],
    'rib_frame': [x/2 for x in range(6, 21)],
    'lower_tunnel_collar_mm': [x/2 for x in range(0, 11)],
    'upper_tunnel_collar_mm': [x/2 for x in range(0, 11)],
    'window_scale': [.9, 1., 1.1],
}
LIMITS = {'front_movement_mm_at_E1000': 4., 'raw_peak_tensile_MPa': 10.125}
FIXED = {'seat_webs': True, 'infill_percent': 5}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def search_signature(h):
    return hashlib.sha256(canonical({'evaluator': source_hash(), 'genes': GENES,
        'fixed': FIXED, 'limits': LIMITS, 'h': h, 'algorithm_version': 1,
        'search_source': Path(__file__).read_text(encoding='utf-8'),
        'dependencies': {p: importlib.metadata.version(p) for p in
                         ['numpy', 'scipy', 'scikit-fem', 'gmsh', 'shapely']}}).encode()).hexdigest()


def decode(genome):
    return {**FIXED, **{key: choices[int(g)] for (key, choices), g in zip(GENES.items(), genome)}}


def encode(params):
    result = []
    for key, choices in GENES.items():
        value = params.get(key, choices[0])
        result.append(choices.index(value) if value in choices else
                      int(np.argmin([abs(x-value) for x in choices])))
    return np.array(result, dtype=int)


class Evaluator:
    def __init__(self, h):
        self.h = h
        self.signature = search_signature(h)
        self.folder = D/'search-evidence'/self.signature[:16]
        self.folder.mkdir(parents=True, exist_ok=True)
        self.cache = {}
        self.models = {}
        self.fresh = 0
        for p in self.folder.glob('candidate-*.json'):
            row = json.loads(p.read_text())
            assert row['search_signature'] == self.signature
            self.cache[row['id']] = row

    def evaluate(self, genome):
        params = decode(genome)
        ident = hashlib.sha256(canonical(params).encode()).hexdigest()[:20]
        if ident in self.cache:
            return self.cache[ident]
        try:
            scale = params['window_scale']
            if scale not in self.models:
                self.models[scale] = Screen(h=self.h, window_scale=scale)
            raw = self.models[scale].solve(params)
            # Timings are operational metadata, excluded from the deterministic ledger.
            raw.pop('elapsed_seconds', None)
            violation = sum(max(0., raw[k]/limit-1.) for k, limit in LIMITS.items())
            feasible = violation == 0
            score = raw['nominal_mass_proxy_g_at_1p24'] if feasible else 1000.+1000.*violation+raw['nominal_mass_proxy_g_at_1p24']
            row = {'id': ident, 'search_signature': self.signature, 'genome': list(map(int, genome)),
                   'parameters': params, 'status': 'SCREEN_FEASIBLE' if feasible else 'SCREEN_REJECTED',
                   'constraint_violation': violation, 'score': score, 'result': raw,
                   'requires_actual_slice_and_3D_validation': True}
        except (AssertionError, RuntimeError) as error:
            row = {'id': ident, 'search_signature': self.signature, 'genome': list(map(int, genome)),
                   'parameters': params, 'status': 'NUMERICAL_REJECTED',
                   'constraint_violation': 1e6, 'score': 1e9, 'reason': str(error),
                   'requires_actual_slice_and_3D_validation': True}
        (self.folder/f'candidate-{ident}.json').write_text(json.dumps(row, indent=2)+'\n')
        self.cache[ident] = row
        self.fresh += 1
        return row


def starter_genomes():
    paths = [ROOT/'designs/rev-f/selected-layout.json',
             ROOT/'analysis/rev-f/full-plane-layout.json',
             ROOT/'analysis/rev-f/light-full-layout.json']
    seeds = [encode(json.loads(p.read_text())) for p in paths]
    light = json.loads(paths[-1].read_text())
    for change in [
            {'skin_mm': .6, 'bottom_band': 1.2, 'diagonal_band': 1.2, 'seat_band': 2.5},
            {'walls': 2, 'plane_mm': .6, 'skin_mm': .6},
            {'walls': 1, 'skin_mm': 1.2, 'plane_mm': 1.2,
             'lower_tunnel_collar_mm': 5., 'upper_tunnel_collar_mm': 5.},
            {'walls': 4, 'skin_mm': 1.2, 'plane_mm': 1.2,
             'bottom_band': 5., 'diagonal_band': 5., 'seat_band': 10.}]:
        seeds.append(encode({**light, **change}))
    return seeds


def run(seed, population_size, generations, h, tag=None):
    validation = json.loads((D/'fast-screen-validation.json').read_text())
    assert validation['status'] == 'PASS' and validation['source_hash'] == source_hash()
    rng = np.random.default_rng(seed)
    maximum = np.array([len(x)-1 for x in GENES.values()], dtype=int)
    evaluator = Evaluator(h)
    (D/'search-definition.json').write_text(json.dumps({'genes': GENES,
        'fixed_parameters': FIXED, 'screen_limits': LIMITS,
        'search_signature': evaluator.signature, 'required_3D_strength_ratio': 4,
        'total_movement_limit_mm': 5, 'provisional_rail_mount_reserve_mm': 1,
        'mass_objective': 'Quadrature proxy during search; actual Orca plastic volume for finalist selection.'}, indent=2)+'\n')
    population = starter_genomes()
    while len(population) < population_size:
        population.append(rng.integers(0, maximum+1))
    population = population[:population_size]
    ledger = []
    folder = D/'runs'/f"{tag or ('seed-'+str(seed))}-h{h:g}"
    folder.mkdir(parents=True, exist_ok=True)
    encountered = {}
    for generation in range(generations+1):
        rows = []
        for genome in population:
            row = evaluator.evaluate(genome)
            rows.append(row)
            encountered[row['id']] = row
        ranked = sorted(rows, key=lambda r: (r['score'], r['id']))
        best = ranked[0]
        entry = {'generation': generation,
                 'population': [r['id'] for r in rows],
                 'best_id': best['id'], 'best_score': best['score'],
                 'feasible_in_population': sum(r['status'] == 'SCREEN_FEASIBLE' for r in rows),
                 'unique_candidates_so_far': len(encountered)}
        ledger.append(entry)
        (folder/'generations.json').write_text(json.dumps(ledger, indent=2)+'\n')
        (folder/'best.json').write_text(json.dumps(best, indent=2)+'\n')
        print('GENERATION', seed, generation, 'best', best['id'], best['score'],
              'feasible', entry['feasible_in_population'], 'evaluated', len(encountered), flush=True)
        if generation == generations:
            break
        # Elitism plus deterministic tournament selection, uniform crossover
        # and bounded integer mutation. Every fourth generation adds immigrants.
        elite_count = max(2, population_size//8)
        next_population = [np.array(r['genome']) for r in ranked[:elite_count]]
        seen = {tuple(g) for g in next_population}
        def tournament():
            sample = [rows[int(i)] for i in rng.integers(0, len(rows), size=3)]
            return min(sample, key=lambda r: (r['score'], r['id']))['genome']
        attempts = 0
        while len(next_population) < population_size:
            attempts += 1
            if (generation+1) % 4 == 0 and len(next_population) >= population_size-2:
                child = rng.integers(0, maximum+1)
            else:
                a, b = np.array(tournament()), np.array(tournament())
                child = np.where(rng.random(len(maximum)) < .5, a, b)
                mask = rng.random(len(maximum)) < .22
                if not mask.any():
                    mask[int(rng.integers(len(mask)))] = True
                for i in np.flatnonzero(mask):
                    if rng.random() < .25:
                        child[i] = rng.integers(maximum[i]+1)
                    else:
                        radius = max(1, int(np.ceil(maximum[i]*(.25 if generation < generations/2 else .1))))
                        child[i] = np.clip(child[i]+rng.integers(-radius, radius+1), 0, maximum[i])
            if tuple(child) in seen and attempts < population_size*100:
                continue
            next_population.append(child)
            seen.add(tuple(child))
        population = next_population
    summary = {'seed': seed, 'population_size': population_size, 'generations': generations,
               'mesh_h_mm': h, 'search_signature': evaluator.signature,
               'evaluated_candidate_ids': sorted(encountered),
               'best_candidate': min(encountered.values(), key=lambda r: (r['score'], r['id'])),
               'generation_ledger_sha256': hashlib.sha256(canonical(ledger).encode()).hexdigest(),
               'optimizer': 'seeded integer genetic algorithm with tournament selection, crossover, mutation and elitism',
               'physical_qualification': False}
    (folder/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print('COMPLETE', folder.relative_to(ROOT), 'unique', len(encountered), 'fresh', evaluator.fresh,
          'ledger', summary['generation_ledger_sha256'], flush=True)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=20260910)
    parser.add_argument('--population', type=int, default=32)
    parser.add_argument('--generations', type=int, default=20)
    parser.add_argument('--h', type=float, default=2.)
    parser.add_argument('--tag')
    args = parser.parse_args()
    run(args.seed, args.population, args.generations, args.h, args.tag)
