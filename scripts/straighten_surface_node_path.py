# -*- coding: utf-8 -*-
"""Align nearby nodes of a user-selected Mecway mesh surface to a 3D line.

Author: Mishal Mohanlal
Version: 2.1.0
Runtime: Mecway's embedded IronPython 2.7 (no external packages).

This is a geometric row-finding tool, NOT an element-edge-chain finder:
it chooses one nearby surface node per longitudinal station. These nodes can
subsequently be connected by beam elements even if they did not originally
share element edges.

1. Back up the model.
2. Select the MESH FACES of the surface where the line is required.
3. Run script, supply start and end node IDs (both on selected faces).
4. Give a search radius in METRES (0 = automatic, about one mesh pitch).
5. Inspect the preview and click Accept or Cancel in the dialog.

Endpoints do not move, nor does this script create any elements. Projection
onto the exact straight line may deform the surrounding mesh, especially if
it is curved. Inspect the edited mesh before structural analysis.
"""

import math

SCRIPT_NAME = 'Straighten Surface Node Path'
VERSION = '2.1.0'
AUTO_RADIUS_PITCH = 1.20
# Minimum projected spacing between consecutive selected nodes.
MIN_STEP_PITCH = 0.30
# Maximum gap for a well-supported proposed line: a gap longer than this
# indicates missing nearby mesh nodes; fail rather than skip a large area.
MAX_GAP_PITCH = 2.75
# Avoid quadratic work if too many nodes happen to be close to the line.
MAX_CANDIDATES = 12000
MAX_IDS_SHOWN = 24
# A selected face should not develop a near-zero distance between any two of
# its previously distinct nodes. Reject before moving anything.
MIN_PAIR_DISTANCE_RATIO = 0.12
MIN_ORIENTED_AREA_RATIO = 0.08


def subtract(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def scale(a, amount):
    return (a[0] * amount, a[1] * amount, a[2] * amount)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def distance(a, b):
    v = subtract(a, b)
    return math.sqrt(dot(v, v))


def median(numbers):
    ordered = sorted(numbers)
    count = len(ordered)
    if not count:
        raise ValueError('No usable mesh spacing could be determined.')
    middle = count // 2
    if count % 2:
        return ordered[middle]
    return 0.5 * (ordered[middle - 1] + ordered[middle])


def node_location(node_id):
    p = mw.node(node_id)
    return (float(p.x), float(p.y), float(p.z))


def prompt_node_id(message):
    answer = mw.input(message)
    if answer is None or str(answer).strip() == '':
        return None
    try:
        value = int(str(answer).strip())
    except (ValueError, TypeError):
        raise ValueError('Node numbers must be positive integers.')
    if value <= 0:
        raise ValueError('Node numbers must be positive integers.')
    return value


def prompt_radius():
    value = mw.input('Maximum node movement / search radius in metres '
                     '(0 or blank = automatic):')
    if value is None:
        return None
    if str(value).strip() == '':
        return 0.0
    try:
        result = float(str(value).strip())
    except (ValueError, TypeError):
        raise ValueError('Radius must be a valid distance in metres.')
    if result < 0.0 or math.isnan(result) or math.isinf(result):
        raise ValueError('Radius must be finite and >= 0.')
    return result


def make_surface(faces):
    """Return face node lists and adjacency used to isolate the surface.

    Unlike the v1 search, adjacency is NOT used as a shortcut edge/path.
    Faces sharing any node belong to the same connected surface component.
    """
    face_lists = []
    adjacency = {}
    for face in faces:
        unique = []
        seen = set()
        for node_id in mw.face_nodes(face):
            node_id = int(node_id)
            if node_id not in seen:
                unique.append(node_id)
                seen.add(node_id)
                if node_id not in adjacency:
                    adjacency[node_id] = set()
        if len(unique) < 2:
            continue
        face_lists.append(unique)
        # A face is a local surface neighbourhood (tri3, quad4, tri6, etc).
        for index, a in enumerate(unique):
            adjacency[a].update(unique[:index])
            adjacency[a].update(unique[index + 1:])
    return face_lists, adjacency


def component_containing(adjacency, start):
    reached = set([start])
    remaining = [start]
    while remaining:
        node_id = remaining.pop()
        for other in adjacency[node_id]:
            if other not in reached:
                reached.add(other)
                remaining.append(other)
    return reached


def estimate_pitch(positions, adjacency, component, ab, a, length):
    """Estimate a representative LOCAL mesh pitch around the entire line.

    Collect each node's nearest nonzero co-face distance. Limit sampling
    to the line's bounding region to avoid distant fine mesh altering the
    pitch. Use the whole component if too few local samples were found.
    """
    all_pitches = []
    local_pitches = []
    ab_unit = scale(ab, 1.0 / length)
    for node_id in component:
        p = positions[node_id]
        nearest = None
        for other in adjacency[node_id]:
            if other not in component:
                continue
            value = distance(p, positions[other])
            if value > 0.0 and (nearest is None or value < nearest):
                nearest = value
        if nearest is None:
            continue
        all_pitches.append(nearest)
        s = dot(subtract(p, a), ab_unit)
        closest = add(a, scale(ab_unit, s))
        d = distance(p, closest)
        if -2.0 * nearest <= s <= length + 2.0 * nearest and d <= 3.0 * nearest:
            local_pitches.append(nearest)
    values = local_pitches if len(local_pitches) >= 3 else all_pitches
    return median(values)


def candidate_points(positions, component, start, end, pitch, radius):
    """Sorted points: (distance along AB, node ID, perpendicular vector, d).

    Coordinates are represented in the line's own 3D orthogonal system:
    lateral vectors are in Cartesian coordinates but perpendicular to AB.
    """
    a = positions[start]
    b = positions[end]
    v = subtract(b, a)
    length = distance(a, b)
    unit = scale(v, 1.0 / length)
    result = [(0.0, start, (0.0, 0.0, 0.0), 0.0)]
    for node_id in component:
        if node_id == start or node_id == end:
            continue
        w = subtract(positions[node_id], a)
        station = dot(w, unit)
        if station <= 0.0 or station >= length:
            continue
        transverse = subtract(w, scale(unit, station))
        offset = math.sqrt(dot(transverse, transverse))
        if offset <= radius + pitch * 1.0e-10:
            result.append((station, node_id, transverse, offset))
    result.append((length, end, (0.0, 0.0, 0.0), 0.0))
    result.sort(key=lambda item: (item[0], item[1]))
    if len(result) > MAX_CANDIDATES:
        raise ValueError('Too many nearby nodes (%d). Please select a '
                         'smaller surface region.' % len(result))
    return result


def optimize_row(candidates, pitch, adjacency, length):
    """Dynamic programming on strictly increasing line stations.

    Unlike mesh-edge Dijkstra, this allows a sensible succession of mesh
    nodes even if the target line crosses faces at arbitrary angles. The
    cost penalizes lateral movement, transverse hopping between rows and
    gaps much larger/smaller than the local mesh pitch.
    """
    n = len(candidates)
    if n < 3:
        return [candidates[0], candidates[-1]]

    # Target gap approximates local mesh pitch, but don't create unnecessary
    # close nodes simply because the total segment is short.
    min_step = max(MIN_STEP_PITCH * pitch, length * 1.0e-10)
    max_gap = max(MAX_GAP_PITCH * pitch, length * 1.0e-10)
    infinity = float('inf')
    best = [infinity] * n
    predecessor = [-1] * n
    best[0] = 0.0
    # Local two-face neighbourhood prevents jumping across folded/overlapping
    # parts of a surface just because their nodes are close in 3D.
    neighbourhood_cache = {}

    def local_neighbours(node_id):
        if node_id not in neighbourhood_cache:
            direct = adjacency[node_id]
            near = set(direct)
            for neighbour in direct:
                near.update(adjacency[neighbour])
            neighbourhood_cache[node_id] = near
        return neighbourhood_cache[node_id]

    # Efficient sliding predecessor window in sorted station order.
    left = 0
    for j in range(1, n):
        s_j, id_j, perp_j, d_j = candidates[j]
        while left < j and s_j - candidates[left][0] > max_gap:
            left += 1
        for i in range(left, j):
            if best[i] == infinity:
                continue
            s_i, id_i, perp_i, d_i = candidates[i]
            step = s_j - s_i
            if step < min_step:
                continue
            # A selected row must remain continuous on the actual mesh
            # surface; near in 3D is not enough on folded geometry.
            near = local_neighbours(id_i)
            if id_j not in near:
                continue
            # Penalize gaps substantially more than short steps. Do not force
            # one node per target 'column', which fails on diagonal rows.
            normalized_step = step / pitch
            gap_cost = 2.0 * max(0.0, normalized_step - 1.1) ** 2
            short_cost = 0.30 * max(0.0, 0.9 - normalized_step) ** 2
            # This regularizes transverse switches between equally close rows.
            lateral_switch = distance(perp_i, perp_j) / pitch
            switching_cost = 1.4 * lateral_switch ** 2
            # Indirect neighbours are OK: eventual beams can be created
            # directly between nodes; don't force stepped mesh-edge paths.
            neighbourhood_cost = 0.0
            if id_j not in adjacency[id_i]:
                neighbourhood_cost = 0.25
            node_cost = 0.05 + 2.5 * (d_j / pitch) ** 2
            # Cost of moving only points near the target and keeping a
            # relatively even spacing along the line.
            value = (best[i] + gap_cost + short_cost + switching_cost
                     + neighbourhood_cost + node_cost)
            if value < best[j] - 1.0e-12:
                best[j] = value
                predecessor[j] = i
    if predecessor[-1] < 0:
        return None
    indices = []
    i = n - 1
    while i >= 0:
        indices.append(i)
        i = predecessor[i]
    indices.reverse()
    return [candidates[index] for index in indices]


def quality_checks(face_lists, positions, selected, updates):
    """Preflight catastrophic node coincidence from moving a subset.

    Checks distinct vertex pairs in each affected face, not just along the
    proposed row. This is a conservative heuristic, NOT an FEA quality metric.
    """
    min_ratio = 1.0
    for face in face_lists:
        if not any(node_id in updates for node_id in face):
            continue
        for i in range(len(face)):
            n1 = face[i]
            for n2 in face[i + 1:]:
                original_length = distance(positions[n1], positions[n2])
                if original_length <= 0.0:
                    continue
                after1 = updates.get(n1, positions[n1])
                after2 = updates.get(n2, positions[n2])
                ratio = distance(after1, after2) / original_length
                if ratio < min_ratio:
                    min_ratio = ratio
    if min_ratio < MIN_PAIR_DISTANCE_RATIO:
        raise ValueError('Potentially collapsed element face: a pair of '
                         'nodes becomes %.1f%% of its original separation. '
                         'Reduce tolerance, remesh or change endpoints. '
                         'No nodes moved.' % (100.0 * min_ratio))
    # On tri3/quad4 faces, also catch near-zero or reversed oriented surface
    # area. This is a conservative preflight, not a full Jacobian check.
    def cross(a, b):
        return (a[1] * b[2] - a[2] * b[1],
                a[2] * b[0] - a[0] * b[2],
                a[0] * b[1] - a[1] * b[0])

    for face in face_lists:
        if not any(node_id in updates for node_id in face):
            continue
        if len(face) not in (3, 4):
            continue
        tris = [(face[0], face[1], face[2])]
        if len(face) == 4:
            tris.append((face[0], face[2], face[3]))
        for n0, n1, n2 in tris:
            original = cross(subtract(positions[n1], positions[n0]),
                             subtract(positions[n2], positions[n0]))
            original_sq = dot(original, original)
            if original_sq <= 1.0e-30:
                continue
            p0 = updates.get(n0, positions[n0])
            p1 = updates.get(n1, positions[n1])
            p2 = updates.get(n2, positions[n2])
            current = cross(subtract(p1, p0), subtract(p2, p0))
            area_ratio = dot(original, current) / original_sq
            if area_ratio < MIN_ORIENTED_AREA_RATIO:
                raise ValueError('Selected node movement would collapse or '
                                 'reverse a surface triangle (signed area '
                                 'ratio %.3f). Try a smaller radius or '
                                 'remesh. No nodes moved.' % area_ratio)
    return min_ratio


def apply_updates(updates, originals):
    changed = []
    try:
        for node_id in sorted(updates):
            new = updates[node_id]
            changed.append(node_id)
            mw.set_node_x(node_id, float(new[0]))
            mw.set_node_y(node_id, float(new[1]))
            mw.set_node_z(node_id, float(new[2]))
    except Exception:
        # Best-effort rollback; saving a backup first is still essential.
        for node_id in reversed(changed):
            old = originals[node_id]
            try:
                mw.set_node_x(node_id, float(old[0]))
                mw.set_node_y(node_id, float(old[1]))
                mw.set_node_z(node_id, float(old[2]))
            except Exception:
                pass
        raise


def confirm_alignment(report):
    """Display a true Accept/Cancel dialog using Windows Forms (IronPython).

    A Cancel click, the X close button, or Escape leaves the model unchanged.
    Return True only when the user explicitly clicks Accept (or presses Enter).
    """
    try:
        import clr
        clr.AddReference('System.Windows.Forms')
        from System.Windows.Forms import (Form, TextBox, Button,
            FormStartPosition, FormBorderStyle, ScrollBars, DialogResult)
    except Exception as exc:
        raise RuntimeError('Cannot open the Windows confirmation dialog: %s. '
                           'No nodes were moved.' % str(exc))

    dialog = Form()
    try:
        dialog.Text = 'Confirm surface node alignment'
        dialog.StartPosition = FormStartPosition.CenterScreen
        dialog.FormBorderStyle = FormBorderStyle.FixedDialog
        dialog.MaximizeBox = False
        dialog.MinimizeBox = False
        dialog.Width = 760
        dialog.Height = 565

        preview = TextBox()
        preview.Multiline = True
        preview.ReadOnly = True
        preview.ScrollBars = ScrollBars.Both
        preview.WordWrap = False
        preview.Left = 14
        preview.Top = 14
        preview.Width = 716
        preview.Height = 456
        preview.Text = report + ('\r\n\r\nClick Accept to move the nodes, '
                                 'or Cancel to leave the mesh unchanged.')

        accept = Button()
        accept.Text = 'Accept'
        accept.Left = 456
        accept.Top = 480
        accept.Width = 130
        accept.Height = 32
        accept.DialogResult = DialogResult.OK

        cancel = Button()
        cancel.Text = 'Cancel'
        cancel.Left = 600
        cancel.Top = 480
        cancel.Width = 130
        cancel.Height = 32
        cancel.DialogResult = DialogResult.Cancel

        dialog.Controls.Add(preview)
        dialog.Controls.Add(accept)
        dialog.Controls.Add(cancel)
        dialog.AcceptButton = accept
        dialog.CancelButton = cancel
        return dialog.ShowDialog() == DialogResult.OK
    finally:
        dialog.Dispose()


def main():
    faces = list(mw.selected_faces())
    if not faces:
        mw.message('Select the surface MESH FACES first, then run this script. '
                   'CAD face selection alone does not supply mesh nodes.')
        return

    start = prompt_node_id('Start node ID on selected surface:')
    if start is None:
        return
    end = prompt_node_id('End node ID on selected surface:')
    if end is None:
        return
    if start == end:
        raise ValueError('Start and end nodes must be different.')
    requested = prompt_radius()
    if requested is None:
        return

    face_lists, adjacency = make_surface(faces)
    if start not in adjacency or end not in adjacency:
        raise ValueError('Both endpoint nodes must belong to the selected '
                         'surface faces. No nodes moved.')
    component = component_containing(adjacency, start)
    if end not in component:
        raise ValueError('Endpoints are on disconnected selected surface '
                         'regions. No nodes moved.')

    positions = dict((node_id, node_location(node_id)) for node_id in component)
    a, b = positions[start], positions[end]
    ab = subtract(b, a)
    length = distance(a, b)
    if length <= 0.0:
        raise ValueError('Endpoint nodes have identical coordinates.')

    pitch = estimate_pitch(positions, adjacency, component, ab, a, length)
    radius = requested if requested else AUTO_RADIUS_PITCH * pitch
    if radius <= 0:
        raise ValueError('Mesh pitch and search radius must be positive.')
    candidates = candidate_points(positions, component, start, end,
                                  pitch, radius)
    path = optimize_row(candidates, pitch, adjacency, length)
    if path is None:
        raise ValueError('No continuous row can be found within the '
                         'selected radius without large spacing gaps. '
                         'Increase the radius carefully, or remesh nearer '
                         'the reference line. No nodes moved.')
    if len(path) <= 2:
        mw.message('No intermediate surface nodes are close enough to '
                   'form an alignment. Nothing changed.')
        return

    unit = scale(ab, 1.0 / length)
    updates = {}
    projected = []
    for station, node_id, transverse, offset in path[1:-1]:
        xyz = add(a, scale(unit, station))
        updates[node_id] = xyz
        projected.append(offset)
    minimum_ratio = quality_checks(face_lists, positions, component, updates)

    gaps = [path[i + 1][0] - path[i][0] for i in range(len(path) - 1)]
    maximum_gap = max(gaps)
    maximum_move = max(projected)
    mean_move = sum(projected) / float(len(projected))
    ids = [str(item[1]) for item in path[:MAX_IDS_SHOWN]]
    if len(path) > MAX_IDS_SHOWN:
        ids.append('... (%d more)' % (len(path) - MAX_IDS_SHOWN))
    warning = ''
    if maximum_move > 0.45 * pitch:
        warning += '\nWARNING: Node movements exceed 45% of mesh pitch.'
    if minimum_ratio < 0.35:
        warning += '\nWARNING: Some face-node separations shrink substantially.'

    report = ('%s v%s\n\n'
              'Selected mesh faces: %d\n'
              'Connected surface nodes: %d\n'
              'Fixed anchors: %d and %d\n'
              'Line length: %.6g m\n'
              'Estimated local mesh pitch: %.6g m\n'
              'Search radius: %.6g m\n'
              'Nodes to move: %d\n'
              'Largest movement: %.6g m\n'
              'Average movement: %.6g m\n'
              'Largest beam-node gap: %.6g m\n'
              'Smallest retained face-node distance ratio: %.3f\n'
              'Selected node IDs: %s%s' %
              (SCRIPT_NAME, VERSION, len(faces), len(component),
               start, end, length, pitch, radius, len(updates),
               maximum_move, mean_move, maximum_gap, minimum_ratio,
               ', '.join(ids), warning))
    if not confirm_alignment(report):
        mw.message('Cancelled. No nodes were moved.')
        return
    apply_updates(updates, positions)
    mw.message('Aligned %d intermediate surface nodes onto the line '
               'from %d to %d. Anchors unchanged.\n\n'
               'The resulting node IDs (in order) are: %s\n\n'
               'Review element distortion before analysis. Beam elements '
               'have NOT been created.' %
               (len(updates), start, end,
                ', '.join(str(item[1]) for item in path)))


try:
    main()
except Exception as err:
    mw.message('%s v%s: %s' % (SCRIPT_NAME, VERSION, str(err)))
