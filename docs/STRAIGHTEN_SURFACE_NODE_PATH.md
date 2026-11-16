# Straighten a surface mesh node path

**Script:** [`../scripts/straighten_surface_node_path.py`](../scripts/straighten_surface_node_path.py)  
**Author:** Mishal Mohanlal  
**Version:** 1.0.0  
**Runtime:** Mecway embedded IronPython 2.7; no external packages.

## Objective

Choose a mesh surface, enter two existing node IDs and move a **single connected row of nearby surface nodes** onto the **straight 3-D line segment** joining the two endpoints. The resulting collinear mesh nodes can then be used to position beams along the mesh.

This edits **the mesh, not CAD geometry**, and does **not** create beams or new elements.

## Instructions

1. Save a **backup** of the Mecway `.liml` file. Test first on a small model.
2. Switch to **mesh face selection** and select **all mesh faces** that the desired row may traverse. Merely selecting an underlying CAD face is not sufficient.
3. Run `straighten_surface_node_path.py` through **Tools → Scripts** (register once using **Tools → Scripts... → New**).
4. Enter the **start node ID**, **end node ID**, and the maximum allowable distance from the straight line **in metres**. Enter `0` or leave it blank for automatic tolerance (1.25 times the estimated mesh pitch).
5. The script reports the proposed node path, maximum movement and average movement. Type the exact word **YES** to make the changes. Anything else cancels without modifying the model.
6. Review the result and inspect the element quality before placing beam elements.

## How the path is found

- Collect mesh nodes incident on the selected faces (`mw.selected_faces()` and `mw.face_nodes()`). The two supplied endpoints **must both belong to these faces**.
- Construct a connectivity graph linking mesh nodes that **share a selected face**. This allows both linear and quadratic face meshes without relying on element-specific node ordering; face diagonals may also be traversed.
- Search for a **single connected path** from start to end. Nodes must progress monotonically along the straight line, remain within the allowed lateral-distance corridor, and a weighted shortest-path search favours nodes near the target line.
- Project intermediate path nodes onto the **infinite line** at their original longitudinal parameter. Because the path is constrained to the segment, the projected nodes lie **between the endpoints**.
- **Keep both endpoint nodes unchanged.** Other mesh nodes, element IDs and element connectivity are also unchanged.

The operation can distort neighbouring surface/solid elements because it moves their shared nodes. It cannot guarantee a physically valid mesh, maintain curvature, or keep the resulting straight line exactly on a curved CAD face. For a sharply curved surface or a coarse/irregular mesh, remeshing or a different approach may be necessary.

## Distance tolerance and units

All Mecway API coordinates and input distances are **SI metres**, even when the GUI displays millimetres. For example:

| Desired distance | Input value (m) |
|---|---:|
| 5 mm | `0.005` |
| 20 mm | `0.02` |
| 100 mm | `0.1` |

If the script reports **No forward-connected node path**, either select additional contiguous mesh faces, increase the distance tolerance cautiously, or consider whether the selected mesh has a row running approximately between the endpoints. A large tolerance can let the path move onto the wrong part of a complicated surface.

## Limits and assumptions

- The search requires a **mesh face selection** and two existing surface mesh nodes; it does not select faces interactively while the script is running.
- The algorithm detects a **geometric co-face path** rather than strictly following element edges. It does not create an ordered line2/beam-element chain.
- Each point on the chosen path must make strictly positive progress along the start-to-end direction. Some unusual meshes or winding surfaces may have no feasible path.
- The change is applied only after a confirmation prompt. If the API rejects an edit midway, the script attempts to restore previously modified nodes, but this is not a substitute for saving a backup.
- Check for collapsed or inverted elements, excessive skewness and inappropriate movement off the original geometry.

## API reference

The implemented Mecway API calls (`selected_faces`, `face_nodes`, `node`, `set_node_x`, `set_node_y`, `set_node_z`, `input`, `message`) are demonstrated or discussed on the [Mecway Python API forum](https://mecway.com/forum/discussion/1020/python-api-scripts) and [Mecway Python API Scripts page 2](https://mecway.com/forum/discussion/1020/python-api-scripts/p2). See also your installed version's **Help → API reference**.
