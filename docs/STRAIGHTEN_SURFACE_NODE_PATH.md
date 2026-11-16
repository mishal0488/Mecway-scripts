# Straighten Surface Node Path — v2.1.0

**Author:** Mishal Mohanlal  
**Runtime:** Mecway built-in IronPython 2.7  
**File:** [`../scripts/straighten_surface_node_path.py`](../scripts/straighten_surface_node_path.py)

## What changed from v1

Version 1 required consecutive nodes to have increasing projections on the target line and allowed an arbitrary jump between any two nodes sharing a face. This made it unreliable with angled, irregular or quadratic meshes, and it could pick sparse or unsuitable nodes.

Version 2 **does not construct a mesh-edge path**. It finds a *geometrically well-spaced sequence of mesh nodes* along the target line, using dynamic programming with a score for:

- How far each candidate would have to move onto the line.
- How regularly selected nodes are spaced along the line.
- Whether adjacent chosen nodes lie on nearby mesh faces (within two face neighbourhoods).
- Whether a choice switches unnecessarily between adjacent mesh rows.

This makes the output useful as the basis of a beam layout: the aligned nodes are collinear, but beam elements have to be added separately. Selected nodes are not necessarily directly connected by existing surface-mesh element edges.

## How to use

1. **Save a backup** of the Mecway model. Start with a simple test mesh.
2. Select **mesh faces** covering the surface region. The script uses Mecway's current selection of *mesh faces*, not CAD entity selections.
3. Run **Tools → Scripts → straighten_surface_node_path.py**. To register it: **Tools → Scripts... → New**, then select the existing `.py` file.
4. Enter the two mesh **node IDs** marking the ends of the desired line. Both must belong to the selected faces and the same connected surface patch.
5. Enter a **maximum search radius / node movement** in **metres**. The default (`0` or blank) uses approximately **1.2 times the local mesh pitch**. For instance, 20 mm is `0.02`, not `20`.
6. Read the summary: selected node IDs, amount of movement, maximum longitudinal gap, and face-node distance ratio.
7. Click **Accept** to move the nodes, or **Cancel** to leave the model unchanged. Closing the dialog also cancels. The preview is read-only and scrollable. The endpoint nodes remain fixed.
8. Inspect the mesh and add beam elements using the collinear nodes as needed. The script **does not create beams or modify existing element connectivity**.

## How it works

Let the start and end nodes define the line segment from **A** to **B**. For every node **P** on the selected surface, calculate its longitudinal station `s` and its perpendicular distance `d` from the line. Candidate nodes must be strictly between the endpoints in station and within the requested distance from the line.

A dynamic-programming search chooses an ordered subset that prefers small perpendicular distance and relatively uniform longitudinal spacing. The search is confined to the surface component containing both endpoints and only allows consecutive selected nodes within two mesh-face neighbourhoods. Unlike v1, it does **not** depend on the monotonicity of *mesh edges* or incorrectly treat every same-face node pair as an existing mesh edge.

Each selected intermediate node is moved to its orthogonal projection on the segment, maintaining its original longitudinal station and not changing node numbers or element connectivity.

### Why 'no continuous row' can still occur

The selected faces may not connect the two anchors sufficiently, or the mesh simply has no suitable intermediate nodes near the ideal line. Try selecting more faces or increasing the search radius cautiously. A very coarse or strongly warped mesh should be remeshed before using this operation.

### Safeguards and limitations

- No coordinates are changed until you click **Accept** in the Windows confirmation dialog. The **Cancel** button and closing the dialog leave the model unchanged.
- The algorithm rejects a line with large missing longitudinal gaps relative to the estimated mesh pitch.
- Selected nodes cannot be projected nearly onto one another; a minimum along-line spacing is enforced.
- It checks for very short inter-node distances within affected faces and tries to reject collapsed / reversed *tri3* or *quad4* face triangles.
- **These tests are conservative heuristics, not an element-quality or Jacobian guarantee.** Always check mesh distortion in Mecway, particularly on 3-D solids, curved or high-order surfaces.
- Since the output must be a perfectly straight **3-D line**, projecting off a curved surface may be significant or geometrically inappropriate. No straight line can remain on a general curved surface throughout its length.
- If the closest-node path would cross non-adjacent surfaces, the local face-continuity constraint is designed to reject this rather than snap unrelated nodes.
- The tool does not generate geometry lines, add beam elements, apply beam properties, make a named selection, remesh or change CAD geometry.

## Validation

Run `python -m unittest discover -s tests -v` from the repository root. The test suite uses a simulated Mecway interface and includes irregular mesh stations, diagonal quadrilateral meshes, warped 3-D surfaces, confirmation handling, disconnected surfaces and collapse safeguards. This validates the geometric algorithm but does **not** substitute for live testing with your installed Mecway API.

Relevant official references: [Mecway Manual — Automation](https://www.mecway.com/manual.pdf), [Mecway forum — face_nodes() and selected_faces()](https://mecway.com/forum/discussion/1020/python-api-scripts/p2), and **Help → API reference** in Mecway.

## Version 2.1.0: button confirmation

The free-text `YES` prompt was replaced by a native Windows Forms modal preview with **Accept** and **Cancel** buttons. No additional Mecway inputs are required. The confirmation dialog is shown only once all selection and mesh checks have completed.
