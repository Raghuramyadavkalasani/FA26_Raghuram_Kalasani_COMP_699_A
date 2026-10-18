"""Validation of interval semantics and generated input integrity."""
import unittest
from prepare_inputs import generate, validate, overlaps, summarize

class InputTests(unittest.TestCase):
    def test_seed_repeatability_and_variation(self):
        self.assertEqual(generate(seed=699), generate(seed=699))
        self.assertNotEqual(generate(seed=699), generate(seed=700))

    def test_generator_constraints(self):
        rows = generate(1000, 7, 1)
        validate(rows, 7)
        self.assertEqual(len(rows), 1000)
        self.assertTrue(all(r['end_minute'] - r['start_minute'] in [15, 30, 60, 120] for r in rows))

    def test_invalid_records_rejected(self):
        row = dict(request_id=1, equipment_id=1, start_minute=0, end_minute=60)
        cases = [[row, row], [row | {'start_minute': 60}], [row | {'end_minute': -1}],
                 [row | {'equipment_id': 0}], [row | {'equipment_id': 3}],
                 [row | {'request_id': 0}], [row | {'end_minute': '60'}],
                 [{k:v for k,v in row.items() if k != 'end_minute'}]]
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                validate(rows, 2)

    def test_boundary_and_overlap_shapes(self):
        a = dict(equipment_id=1, start_minute=60, end_minute=120)
        for start, end, expected in [(0,60,False),(120,180,False),(60,120,True),
                                     (70,80,True),(0,180,True),(30,90,True),(90,150,True)]:
            b = dict(equipment_id=1, start_minute=start, end_minute=end)
            self.assertEqual(overlaps(a,b), expected)
            self.assertEqual(overlaps(b,a), expected)
        self.assertFalse(overlaps(a, a | {'equipment_id': 2}))

    def test_hand_counted_summary(self):
        rows = [dict(request_id=1, equipment_id=1,start_minute=0,end_minute=60),
                dict(request_id=2, equipment_id=1,start_minute=30,end_minute=90),
                dict(request_id=3, equipment_id=1,start_minute=90,end_minute=120),
                dict(request_id=4, equipment_id=2,start_minute=0,end_minute=60)]
        result = summarize(rows)
        self.assertEqual(result['same_equipment_pairs'], 3)
        self.assertEqual(result['overlapping_input_pairs'], 1)
        self.assertEqual(result['overlap_fraction_of_same_equipment_pairs'], 1/3)

    def test_invalid_generation_parameters(self):
        for count, equipment in [(0,1),(-1,1),(1,0)]:
            with self.assertRaises(ValueError):
                generate(count,equipment)

if __name__ == '__main__':
    unittest.main()
