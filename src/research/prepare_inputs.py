"""AI-assisted Week 1 synthetic input preparation; no approval experiment yet."""
import argparse
import csv
import hashlib
import json
import platform
import random
from collections import Counter
from pathlib import Path

FIELDS = ['request_id', 'equipment_id', 'start_minute', 'end_minute']

def generate(count=200, equipment=10, seed=699):
    if count < 1 or equipment < 1:
        raise ValueError('count and equipment must be positive')
    rng = random.Random(seed)
    return [dict(request_id=i + 1, equipment_id=rng.randint(1, equipment),
                 start_minute=(start := rng.randrange(0, 480, 15)),
                 end_minute=start + rng.choice([15, 30, 60, 120]))
            for i in range(count)]

def validate(rows, equipment):
    seen = set()
    for row in rows:
        if set(row) != set(FIELDS):
            raise ValueError('unexpected or missing columns')
        if any(type(row[k]) is not int for k in FIELDS):
            raise ValueError('fields must be integers')
        if row['request_id'] < 1 or row['request_id'] in seen:
            raise ValueError('invalid or duplicate request ID')
        seen.add(row['request_id'])
        if not 1 <= row['equipment_id'] <= equipment:
            raise ValueError('unknown equipment')
        if not 0 <= row['start_minute'] < row['end_minute']:
            raise ValueError('invalid interval')

def overlaps(a, b):
    return (a['equipment_id'] == b['equipment_id'] and
            a['start_minute'] < b['end_minute'] and
            b['start_minute'] < a['end_minute'])

def summarize(rows):
    possible = sum(a['equipment_id'] == b['equipment_id']
                   for i, a in enumerate(rows) for b in rows[i + 1:])
    conflicts = sum(overlaps(a, b) for i, a in enumerate(rows) for b in rows[i + 1:])
    return {'request_count': len(rows),
            'equipment_used': len({r['equipment_id'] for r in rows}),
            'requests_per_equipment': dict(sorted(Counter(r['equipment_id'] for r in rows).items())),
            'duration_minutes_counts': dict(sorted(Counter(r['end_minute'] - r['start_minute'] for r in rows).items())),
            'same_equipment_pairs': possible, 'overlapping_input_pairs': conflicts,
            'overlap_fraction_of_same_equipment_pairs': conflicts / possible if possible else None}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--count', type=int, default=200)
    parser.add_argument('--equipment', type=int, default=10)
    parser.add_argument('--seed', type=int, default=699)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rows = generate(args.count, args.equipment, args.seed)
    validate(rows, args.equipment)
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / 'requests.csv'
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    with path.open(newline='') as stream:
        loaded = [{k: int(v) for k, v in row.items()} for row in csv.DictReader(stream)]
    validate(loaded, args.equipment)
    if loaded != rows:
        raise ValueError('CSV round-trip mismatch')
    result = {'stage': 'input_preparation_only', 'parameters': vars(args) | {'output': str(args.output)},
              'environment': {'python': platform.python_version(), 'system': platform.system(), 'machine': platform.machine()},
              'csv_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'validation': 'passed; CSV round-trip identical', 'summary': summarize(loaded)}
    (args.output / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
