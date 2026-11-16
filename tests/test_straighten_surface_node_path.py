# -*- coding: utf-8 -*-
"""Lightweight CPython tests with a fake Mecway API (no Mecway install needed).

Run: python -m unittest discover -s tests -v
The production script still targets IronPython 2.7 inside Mecway.
"""
import os
import runpy
import unittest

SCRIPT = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                      '..', 'scripts',
                                      'straighten_surface_node_path.py'))


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


def grid_mesh():
    positions = {}
    for j in range(3):
        for i in range(5):
            node_id = j * 5 + i + 1
            # A slightly wavy bottom row; fixed anchors at i=0 and i=4.
            y = float(j)
            if j == 0 and 0 < i < 4:
                y = 0.12 if i == 2 else 0.08
            positions[node_id] = (float(i), y, 0.0)
    faces = {}
    n = 0
    for j in range(2):
        for i in range(4):
            a = j * 5 + i + 1
            faces[n] = [a, a + 1, a + 6, a + 5]
            n += 1
    return faces, positions


class StraightenTests(unittest.TestCase):
    def test_wavy_row_is_straightened_and_other_rows_untouched(self):
        faces, positions = grid_mesh()
        mw = FakeMecway(faces, positions, ['1', '5', '0', 'YES'])
        runpy.run_path(SCRIPT, init_globals={'mw': mw})
        for node_id in range(1, 6):
            self.assertAlmostEqual(mw.positions[node_id][1], 0.0)
        for node_id in range(6, 16):
            self.assertEqual(mw.positions[node_id], list(positions[node_id]))
        self.assertEqual(set(node_id for node_id, axis, value in mw.writes),
                         set([2, 3, 4]))
        self.assertTrue(any('Moved 3 intermediate' in msg for msg in mw.messages))

    def test_confirmation_is_required(self):
        faces, positions = grid_mesh()
        mw = FakeMecway(faces, positions, ['1', '5', '0.5', 'NO'])
        runpy.run_path(SCRIPT, init_globals={'mw': mw})
        self.assertEqual(mw.writes, [])
        self.assertTrue(any('Cancelled' in msg for msg in mw.messages))

    def test_selected_face_subset_must_include_both_endpoints(self):
        faces, positions = grid_mesh()
        mw = FakeMecway({0: faces[0]}, positions, ['1', '5', '0'])
        runpy.run_path(SCRIPT, init_globals={'mw': mw})
        self.assertEqual(mw.writes, [])
        self.assertTrue(any('must belong' in msg for msg in mw.messages))

    def test_narrow_corridor_can_reject_path(self):
        faces, positions = grid_mesh()
        mw = FakeMecway(faces, positions, ['1', '5', '0.01'])
        runpy.run_path(SCRIPT, init_globals={'mw': mw})
        self.assertEqual(mw.writes, [])
        self.assertTrue(any('No forward-connected' in msg for msg in mw.messages))

    def test_no_face_selection_rejects(self):
        faces, positions = grid_mesh()
        mw = FakeMecway({}, positions, [])
        runpy.run_path(SCRIPT, init_globals={'mw': mw})
        self.assertEqual(mw.writes, [])
        self.assertTrue(any('Select the MESH FACES' in msg for msg in mw.messages))


if __name__ == '__main__':
    unittest.main()
