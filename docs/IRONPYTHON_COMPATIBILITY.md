# Mecway IronPython compatibility guide

**Target runtime:** Embedded IronPython 2.7, per the Mecway v30 manual (consult the API reference installed with your version for changes).

## Supported approach

Mecway supplies special globals when it executes a script:

- `mw`: operations on Mecway and the model.
- `solution`: operations on the solution in the active configuration.
- `Vector`: 3D vector values (e.g. for node positions).
- `FaceId`: identifies an element face.

The scripts in `../scripts/` are meant to be started **inside Mecway**, not by `python script.py` in Anaconda or CPython. The Python standard library and compatible pure-Python modules can be used, subject to the embedded runtime.

## Syntax restrictions

Use Python 2.7-compatible syntax. Avoid f-strings, annotations, dataclasses, the walrus operator, and other Python 3-only syntax. Use `.format()` or `%` formatting rather than f-strings. Keep dependency-free scripts unless a dependency has been verified in IronPython.

Binary CPython extensions (for example standard NumPy and pandas distributions) do not run directly in the embedded IronPython interpreter. For advanced data processing, export data from Mecway and process it using a separate CPython application, if needed.

## Units and verification

Mecway returns physical quantities to scripts in **SI base units**: metres, kilograms, seconds, kelvin, amperes, and radians. For example, node coordinates used by scripts are in **metres**, not necessarily in the units shown on screen. Convert intentionally when reporting results.

The built-in API does **not** expose every Mecway feature; confirm availability in **Help → API reference** before implementation. Build scripts that check selections and input assumptions before changing a mesh. Save a backup before any modification. Run and validate each tool against a small test model first.

## How to register and test

1. In Mecway choose **Tools → Scripts... → New**.
2. Choose an existing file from the repository's `scripts` folder.
3. Run it from the **Tools** menu.
4. For `report_selected_nodes.py`, manually select a few nodes before invoking the script.

## References

- [Mecway manual, chapter 16 Automation](https://www.mecway.com/manual.pdf)
- [Mecway scripting forum](https://mecway.com/forum/discussion/1020/python-api-scripts)
