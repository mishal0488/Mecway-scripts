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
│   └── report_selected_nodes.py
└── docs/
    └── IRONPYTHON_COMPATIBILITY.md
```

## Running the scripts in Mecway

1. Clone or download this repository onto the Windows computer running Mecway.
2. Open Mecway and a model (for scripts needing model data).
3. Choose **Tools → Scripts... → New** and select the desired existing `.py` file in the `scripts` directory.
4. Save any changes to the script in a text editor. Run it from its entry in Mecway's **Tools** menu.
5. Start with `hello_mecway.py`, then select a few mesh nodes and run `report_selected_nodes.py`.

Mecway's built-in scripting globals include `mw`, `solution`, `FaceId`, and `Vector`. The available API is documented in **Help → API reference** inside your installed Mecway version.

## Development rules

- Target **IronPython 2.7** syntax (not Python 3-only features such as f-strings or type hints).
- Avoid packages with CPython binary dependencies, including NumPy and pandas, in in-Mecway scripts.
- Keep scripts directly runnable from Mecway. Do not assume `mw` exists when a script is launched with ordinary Python.
- Mecway API measurements and coordinates use **SI base units** even when the model's display units differ.
- For scripts that change node coordinates or elements, first save a copy of the model and validate the result.
- Check the API reference for the exact installed Mecway version before using version-specific operations.

For compatibility details see [docs/IRONPYTHON_COMPATIBILITY.md](docs/IRONPYTHON_COMPATIBILITY.md).

## References

- [Mecway official manual — Automation, section 16](https://www.mecway.com/manual.pdf)
- [Mecway Python API Scripts forum discussion](https://mecway.com/forum/discussion/1020/python-api-scripts)

## Planned additions

Add future mesh-editing, model setup, quality-checking, analysis and post-processing tools as separate scripts, each with a short description, version, and usage notes.
