# -*- coding: utf-8 -*-
"""Fake Mecway integration + regression tests for the surface aligner.

Run: python -m unittest discover -s tests -v
"""
import os
import runpy
import unittest

SCRIPT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..',
                                      'scripts', 'straighten_surface_node_path.py'))


class Point(object):
    def __init__(self, xyz):
        self.x, self.y, self.z = xyz


class FakeMecway(object):
    def __init__(self, faces, positions, replies):
        self.faces = faces
        self.positions = dict((key, list(value)) for key, value in positions.items())
        self.replies = list(replies)
        self.messages = []
        self.writes = []

    def selected_faces(self):
        return list(self.faces)

    def face_nodes(self, face_id):
        return self.faces[face_id]

    def node(self, node_id):
        return Point(self.positions[node_id])

    def input(self, prompt):
        self.messages.append(prompt)
        return self.replies.pop(0)

    def message(self, value):
        self.messages.append(value)

    def set_node_x(self, node_id, value):
        self.writes.append((node_id, 'x', value))
        self.positions[node_id][0] = value

    def set_node_y(self, node_id, value):
        self.writes.append((node_id, 'y', value))
        self.positions[node_id][1] = value

    def set_node_z(self, node_id, value):
        self.writes.append((node_id, 'z', value))
        self.positions[node_id][2] = value


def grid_mesh(cols=5, rows=3, warp=0.10):
    positions = {}
    for j in range(rows):
        for i in range(cols):
            node_id = j * cols + i + 1
            y = float(j)
            if j == 0 and 0 < i < cols - 1:
                y += warp * (1.0 + (i % 2) * 0.2)
            positions[node_id] = (float(i), y, 0.0)
    faces = {}
    n = 0
    for j in range(rows - 1):
        for i in range(cols - 1):
            a = j * cols + i + 1
            faces[n] = [a, a + 1, a + cols + 1, a + cols]
            n += 1
    return faces, positions


def run_model(faces, positions, replies):
    fake = FakeMecway(faces, positions, replies)
    runpy.run_path(SCRIPT, init_globals={'mw': fake})
    return fake


class StraightenTests(unittest.TestCase):
    def test_wavy_row_and_other_rows_unchanged(self):
        faces, positions = grid_mesh()
        mw = run_model(faces, positions, ['1', '5', '0', 'YES'])
        for node_id in range(1, 6):
            self.assertAlmostEqual(mw.positions[node_id][1], 0.0)
        for node_id in range(6, 16):
            self.assertEqual(mw.positions[node_id], list(positions[node_id]))
        self.assertEqual(set(node_id for node_id, axis, val in mw.writes),
                         set([2, 3, 4]))
        self.assertTrue(any('Aligned 3 intermediate' in msg for msg in mw.messages))

    def test_user_can_cancel_without_changes(self):
        faces, positions = grid_mesh()
        mw = run_model(faces, positions, ['1', '5', '0.5', 'NO'])
        self.assertEqual(mw.writes, [])
        self.assertTrue(any('Cancelled' in msg for msg in mw.messages))

    def test_selected_face_subset_must_include_both_anchors(self):
        faces, positions = grid_mesh()
        mw = run_model({0: faces[0]}, positions, ['1', '5', '0'])
        self.assertEqual(mw.writes, [])
        self.assertTrue(any('must belong' in msg for msg in mw.messages))

    def test_tolerance_too_small_fails_before_editing(self):
        faces, positions = grid_mesh()
        mw = run_model(faces, positions, ['1', '5', '0.01'])
        self.assertEqual(mw.writes, [])
        self.assertTrue(any('No continuous row' in msg or 'No intermediate' in msg
                            for msg in mw.messages))

    def test_no_face_selection_fails(self):
        faces, positions = grid_mesh()
        mw = run_model({}, positions, [])
        self.assertEqual(mw.writes, [])
        self.assertTrue(any('Select the surface MESH FACES' in msg
                            for msg in mw.messages))

    def test_irregular_longitudinal_row(self):
        faces, positions = grid_mesh(cols=7, rows=3, warp=0.15)
        # The station order of adjacent nodes is now no longer strictly
        # increasing (a known failure of the old edge-search algorithm).
        x = [0.0, 0.85, 1.95, 1.88, 4.2, 5.05, 6.0]
        for i, xx in enumerate(x):
            positions[i + 1] = (xx, positions[i + 1][1], 0.0)
        mw = run_model(faces, positions, ['1', '7', '0.6', 'YES'])
        changed = set(node_id for node_id, axis, val in mw.writes)
        self.assertTrue(changed)
        self.assertNotIn(1, changed)
        self.assertNotIn(7, changed)
        for nid in changed:
            self.assertAlmostEqual(mw.positions[nid][1], 0.0)
        self.assertTrue(any('Aligned ' in msg for msg in mw.messages))

    def test_diagonal_route_does_not_collapse_duplicate_station(self):
        faces, positions = grid_mesh(cols=6, rows=6, warp=0)
        mw = run_model(faces, positions, ['1', '36', '1.0', 'YES'])
        # At the same longitudinal coordinate x+y, multiple nodes exist;
        # the algorithm must choose no more than one per close station.
        changed = set(node_id for node_id, axis, val in mw.writes)
        self.assertTrue(changed, '\n'.join(mw.messages))
        stations = []
        for node_id in changed:
            x, y, z = mw.positions[node_id]
            self.assertAlmostEqual(x, y)
            stations.append(x + y)
        stations.sort()
        for a, b in zip(stations, stations[1:]):
            self.assertGreater(b - a, 0.20)

    def test_reject_disconnected_selected_surfaces(self):
        faces = {0: [1, 2, 3], 1: [4, 5, 6]}
        positions = {1: (0, 0, 0), 2: (1, 0, 0), 3: (0, 1, 0),
                     4: (3, 0, 0), 5: (4, 0, 0), 6: (3, 1, 0)}
        mw = run_model(faces, positions, ['1', '5', '0'])
        self.assertFalse(mw.writes)
        self.assertTrue(any('disconnected' in msg for msg in mw.messages))

    def test_short_direct_line_with_no_intermediate_nodes(self):
        faces = {0: [1, 2, 3]}
        positions = {1: (0, 0, 0), 2: (1, 0, 0), 3: (0, 1, 0)}
        mw = run_model(faces, positions, ['1', '2', '0'])
        self.assertFalse(mw.writes)
        self.assertTrue(any('No intermediate' in msg for msg in mw.messages))

    def test_3d_inclined_plane_preserves_longitudinal_coordinates(self):
        faces, positions = grid_mesh(cols=7, rows=3, warp=0.1)
        # Mesh on an inclined plane, with the intended row also wavy in Z.
        for node_id, xyz in list(positions.items()):
            x, y, z = xyz
            positions[node_id] = (x, y, 0.25 * x + 0.10 * y)
        mw = run_model(faces, positions, ['1', '7', '0.5', 'YES'])
        moved = set(n for n, axis, value in mw.writes)
        self.assertEqual(moved, set(range(2, 7)))
        for n in moved:
            x, y, z = mw.positions[n]
            self.assertAlmostEqual(y, 0.0)
            self.assertAlmostEqual(z, 0.25 * x)

    def test_face_inversion_is_rejected(self):
        # Moving node 2 to the target line would flatten this triangle.
        faces = {0: [1, 2, 3]}
        positions = {1: (0.0, 0.0, 0.0),
                     2: (1.0, 0.6, 0.0),
                     3: (2.0, 0.0, 0.0)}
        mw = run_model(faces, positions, ['1', '3', '1.0', 'YES'])
        self.assertFalse(mw.writes)
        self.assertTrue(any(('collapse' in msg) or
                            ('No intermediate' in msg) for msg in mw.messages),
                        '\n'.join(mw.messages))

    def test_selected_node_ids_are_reported_in_order(self):
        faces, positions = grid_mesh()
        mw = run_model(faces, positions, ['1', '5', '0', 'YES'])
        self.assertTrue(any('1, 2, 3, 4, 5' in msg for msg in mw.messages))

    def test_large_mesh_skips_unrelated_other_region(self):
        faces, positions = grid_mesh(cols=18, rows=18, warp=0.05)
        mw = run_model(faces, positions, ['1', '18', '0', 'YES'])
        self.assertEqual(set(node_id for node_id, axis, val in mw.writes),
                         set(range(2, 18)))


if __name__ == '__main__':
    unittest.main()
