# -*- coding: utf-8 -*-
# Mecway embedded IronPython 2.7 script
# Author: Mishal Mohanlal
# Version: 1.0.0
# Purpose: Straighten one connected row of surface mesh nodes between
#          two existing endpoint nodes, without changing element connectivity.
#
# How to use:
#   1. Save a backup copy of the model.
#   2. Select the mesh faces making up the surface of interest in Mecway.
#   3. Run this script from Mecway's Tools menu.
#   4. Enter the start and end node IDs and an optional search tolerance in m.
#   5. Inspect the proposed movement and type YES to apply.
#
# All coordinates and distance inputs are in metres (Mecway API SI units).
# This is a MESH operation, not a modification of underlying CAD geometry.
# The script deliberately does NOT create beam elements.

import heapq
import math

SCRIPT_NAME = "Straighten Surface Node Path"
VERSION = "1.0.0"
AUTO_TOLERANCE_FACTOR = 1.25
LINE_PENALTY = 4.0
MAX_REPORTED_NODES = 25


def distance(a, b):
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    dz = a[2] - b[2]
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def subtract(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def node_position(node_id):
    point = mw.node(node_id)
    return (float(point.x), float(point.y), float(point.z))


def read_node_id(prompt):
    answer = mw.input(prompt)
    if answer is None or str(answer).strip() == "":
        return None
    try:
        node_id = int(str(answer).strip())
    except (TypeError, ValueError):
        raise ValueError("Node ID must be a positive whole number.")
    if node_id <= 0:
        raise ValueError("Node ID must be a positive whole number.")
    return node_id


def median(values):
    ordered = sorted(values)
    count = len(ordered)
    if count == 0:
        raise ValueError("Cannot calculate mesh spacing: no node pairs.")
    mid = count // 2
    if count % 2:
        return ordered[mid]
    return 0.5 * (ordered[mid - 1] + ordered[mid])


def surface_graph(faces):
    """Use co-face node links; works without assuming tri/quad node ordering.

    A co-face link can cross a quad diagonally, so this finds a connected
    geometric path, not necessarily a chain of existing mesh edges.
    """
    graph = {}
    for face_id in faces:
        face_nodes = list(mw.face_nodes(face_id))
        # Remove duplicates (some face representations can repeat corners).
        unique = []
        seen = set()
        for item in face_nodes:
            node_id = int(item)
            if node_id not in seen:
                seen.add(node_id)
                unique.append(node_id)
                if node_id not in graph:
                    graph[node_id] = set()

        # Link every pair in a face. This is deliberately not an assertion
        # that the two nodes share an element edge.
        for index, node_a in enumerate(unique):
            for node_b in unique[index + 1:]:
                graph[node_a].add(node_b)
                graph[node_b].add(node_a)
    return graph


def projected_data(positions, start_id, end_id):
    a = positions[start_id]
    b = positions[end_id]
    direction = subtract(b, a)
    length_sq = dot(direction, direction)
    if length_sq <= 0.0:
        raise ValueError("The two endpoint nodes occupy the same location.")

    data = {}
    for node_id, point in positions.items():
        t = dot(subtract(point, a), direction) / length_sq
        foot = (a[0] + t * direction[0],
                a[1] + t * direction[1],
                a[2] + t * direction[2])
        d = distance(point, foot)
        data[node_id] = (t, d, foot)
    return data, math.sqrt(length_sq)


def estimate_spacing(graph, positions):
    # A robust characteristic mesh pitch from each node's nearest
    # co-face neighbour. Zero-length links are ignored.
    near_lengths = []
    for node_id, neighbours in graph.items():
        lengths = [distance(positions[node_id], positions[other])
                   for other in neighbours]
        lengths = [value for value in lengths if value > 0.0]
        if lengths:
            near_lengths.append(min(lengths))
    return median(near_lengths)


def find_path(graph, positions, projection, start_id, end_id,
              max_offset, spacing, length):
    """Dijkstra: forward-only, close-to-line, face-connected path."""
    # Disallow moves backwards along AB, otherwise a route can weave or
    # repeatedly visit the same longitudinal station.
    t_epsilon = 1.0e-10
    best = {start_id: 0.0}
    previous = {}
    queue = [(0.0, start_id)]
    while queue:
        cost_here, here = heapq.heappop(queue)
        if cost_here > best.get(here, float("inf")):
            continue
        if here == end_id:
            break
        t_here, d_here, unused = projection[here]
        for there in graph[here]:
            t_there, d_there, unused = projection[there]
            if t_there <= t_here + t_epsilon:
                continue
            if t_there > 1.0 + t_epsilon:
                continue
            if d_there > max_offset + length * 1.0e-12:
                continue
            segment = distance(positions[here], positions[there])
            if segment <= 0.0:
                continue
            mean_offset = 0.5 * (d_here + d_there)
            # Prefer a near-line route; disfavor detours across the surface.
            penalty = 1.0 + LINE_PENALTY * (mean_offset / spacing) ** 2
            new_cost = cost_here + segment * penalty
            if new_cost < best.get(there, float("inf")):
                best[there] = new_cost
                previous[there] = here
                heapq.heappush(queue, (new_cost, there))

    if end_id not in best:
        return None
    path = [end_id]
    while path[-1] != start_id:
        path.append(previous[path[-1]])
    path.reverse()
    return path


def move_node(node_id, xyz):
    mw.set_node_x(node_id, float(xyz[0]))
    mw.set_node_y(node_id, float(xyz[1]))
    mw.set_node_z(node_id, float(xyz[2]))


def render_ids(path):
    visible = [str(node_id) for node_id in path[:MAX_REPORTED_NODES]]
    if len(path) > MAX_REPORTED_NODES:
        visible.append("... +%d more" % (len(path) - MAX_REPORTED_NODES))
    return " -> ".join(visible)


def main():
    faces = list(mw.selected_faces())
    if not faces:
        mw.message("Select the MESH FACES of a surface before running this script.\n"
                   "A CAD geometry face selection is not sufficient.")
        return

    start_id = read_node_id("Start node ID (on the selected surface):")
    if start_id is None:
        return
    end_id = read_node_id("End node ID (on the selected surface):")
    if end_id is None:
        return
    if start_id == end_id:
        raise ValueError("Start and end nodes must be different.")

    tolerance_string = mw.input("Maximum distance from line in metres "
                                "(0 or blank = automatic):")
    if tolerance_string is None:
        return
    if str(tolerance_string).strip() == "":
        requested_tolerance = 0.0
    else:
        try:
            requested_tolerance = float(str(tolerance_string).strip())
        except (TypeError, ValueError):
            raise ValueError("Search tolerance must be a number in metres.")
    if requested_tolerance < 0.0 or math.isnan(requested_tolerance) or math.isinf(requested_tolerance):
        raise ValueError("Search tolerance must be finite and nonnegative.")

    graph = surface_graph(faces)
    if start_id not in graph or end_id not in graph:
        raise ValueError("Both endpoint nodes must belong to the selected "
                         "surface MESH FACES. No nodes have been moved.")

    positions = dict((node_id, node_position(node_id)) for node_id in graph)
    projection, line_length = projected_data(positions, start_id, end_id)
    spacing = estimate_spacing(graph, positions)
    max_offset = requested_tolerance or (AUTO_TOLERANCE_FACTOR * spacing)
    path = find_path(graph, positions, projection, start_id, end_id,
                     max_offset, spacing, line_length)
    if path is None:
        raise ValueError("No forward-connected node path was found within "
                         "%.6g m of the line. Try selecting more adjacent "
                         "surface faces or increasing the tolerance. "
                         "No nodes have been moved." % max_offset)

    intermediate = path[1:-1]
    if not intermediate:
        mw.message("The endpoints share a face and the closest path has "
                   "no intermediate nodes to move.\n"
                   "No mesh modification was made.")
        return

    move_distances = [projection[node_id][1] for node_id in intermediate]
    max_move = max(move_distances)
    mean_move = sum(move_distances) / len(move_distances)
    warning = ""
    if max_move > 0.5 * spacing:
        warning = ("\nWARNING: Maximum move exceeds half the estimated "
                   "mesh pitch. Check distortion and element quality.")

    summary = ("%s v%s\n\n"
               "Selected faces: %d\n"
               "Surface nodes: %d\n"
               "Fixed endpoints: %d -> %d\n"
               "Line length: %.6g m\n"
               "Estimated mesh pitch: %.6g m\n"
               "Search tolerance: %.6g m\n"
               "Intermediate nodes to move: %d\n"
               "Maximum move: %.6g m\n"
               "Average move: %.6g m\n"
               "Path: %s%s" %
               (SCRIPT_NAME, VERSION, len(faces), len(graph),
                start_id, end_id, line_length, spacing, max_offset,
                len(intermediate), max_move, mean_move,
                render_ids(path), warning))

    confirmation = mw.input(summary + "\n\nType YES to move these nodes:")
    if confirmation is None or str(confirmation).strip().upper() != "YES":
        mw.message("Cancelled. No nodes were moved.")
        return

    # Compute the entire edit in advance; preserve original endpoints.
    targets = dict((node_id, projection[node_id][2]) for node_id in intermediate)
    changed = []
    try:
        for node_id in intermediate:
            changed.append(node_id)  # include this node in rollback on failure
            move_node(node_id, targets[node_id])
    except Exception:
        # Best-effort restoration if Mecway rejects an individual coordinate.
        for node_id in reversed(changed):
            try:
                move_node(node_id, positions[node_id])
            except Exception:
                pass
        raise

    mw.message("Moved %d intermediate nodes onto the straight line from "
               "node %d to node %d. Endpoints unchanged.\n\n"
               "IMPORTANT: Check mesh distortion/element quality before "
               "using the mesh for analysis or adding beams.\n\n"
               "Path: %s" % (len(intermediate), start_id, end_id,
                              render_ids(path)))


try:
    main()
except Exception as exc:
    mw.message("%s: %s" % (SCRIPT_NAME, str(exc)))
