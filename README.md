# Mecway Scripts

Python automation scripts for **Mecway FEA**, written for Mecway's embedded **IronPython 2.7** environment.

**Author:** Mishal Mohanlal  
**Status:** Starter scripts; test inside your installed Mecway version before use on production models.

## Repository layout

```text
Mecway-scripts/
├── README.md
├── scripts/
│   ├── hello_mecway.py
│   ├── report_selected_nodes.py
│   └── straighten_surface_node_path.py
├── tests/
│   └── test_straighten_surface_node_path.py
└── docs/
    ├── IRONPYTHON_COMPATIBILITY.md
    └── STRAIGHTEN_SURFACE_NODE_PATH.md
```

## Running the scripts in Mecway

1. Clone or download this repository onto the Windows computer running Mecway.
2. Open Mecway and a model (for scripts needing model data).
3. Choose **Tools → Scripts... → New** and select the desired existing `.py` file in the `scripts` directory.
4. Save any changes to the script in a text editor. Run it from its entry in Mecway's **Tools** menu.
5. Start with `hello_mecway.py`, then select a few mesh nodes and run `report_selected_nodes.py`.

### Straighten a path across selected mesh faces (v2.1.0)

`straighten_surface_node_path.py` finds a well-spaced, continuous row of surface nodes near the line between two selected node IDs and projects its intermediate nodes onto that line. Version 2 replaces the brittle edge-by-edge path search with a dynamic-programming selection that accommodates irregular meshes and angled lines. First select the **mesh faces** of the surface, run the script, enter the two node IDs and a search tolerance in **metres**, then click **Accept** or **Cancel** in the preview dialog. Endpoints stay fixed. The operation edits mesh coordinates but **does not create beam elements**.

Save a backup, then inspect mesh distortion and element quality. The script rejects some extreme changes, but these safety tests do not replace a mesh-quality check. Full usage and limitations: [Straighten Surface Node Path](docs/STRAIGHTEN_SURFACE_NODE_PATH.md).

Mecway's built-in scripting globals include `mw`, `solution`, `FaceId`, and `Vector`. The available API is documented in **Help → API reference** inside your installed Mecway version.

## Development rules

- Target **IronPython 2.7** syntax (not Python 3-only features such as f-strings or type hints).
- Avoid packages with CPython binary dependencies, including NumPy and pandas, in in-Mecway scripts.
- Keep scripts directly runnable from Mecway. Do not assume `mw` exists when a script is launched with ordinary Python.
- Mecway API measurements and coordinates use **SI base units** even when the model's display units differ.
- For scripts that change node coordinates or elements, first save a copy of the model and validate the result.
- Check the API reference for the exact installed Mecway version before using version-specific operations.

For compatibility details see [docs/IRONPYTHON_COMPATIBILITY.md](docs/IRONPYTHON_COMPATIBILITY.md).

## Local tests

For logic tests with a simulated Mecway API (using standard CPython), run `python -m unittest discover -s tests -v` from the repository root. These do not replace a live test in Mecway.

## References

- [Mecway official manual — Automation, section 16](https://www.mecway.com/manual.pdf)
- [Mecway Python API Scripts forum discussion](https://mecway.com/forum/discussion/1020/python-api-scripts)

## Planned additions

Add future mesh-editing, model setup, quality-checking, analysis and post-processing tools as separate scripts, each with a short description, version, and usage notes.
