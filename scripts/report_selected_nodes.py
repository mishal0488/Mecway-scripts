# -*- coding: utf-8 -*-
# Mecway embedded IronPython 2.7 script
# Author: Mishal Mohanlal
# Version: 0.1.0
# Purpose: Show coordinates of selected mesh nodes (SI metres).
# This script does not modify the model.

MAX_SHOWN = 30

node_ids = list(mw.selected_nodes())

if not node_ids:
    mw.message("No mesh nodes selected. Select nodes and run this script again.")
else:
    lines = ["Selected nodes: %d" % len(node_ids),
             "Node positions in metres (SI):"]

    for node_id in node_ids[:MAX_SHOWN]:
        p = mw.node(node_id)
        lines.append("%s: X=%.6g, Y=%.6g, Z=%.6g" %
                     (node_id, p.x, p.y, p.z))

    if len(node_ids) > MAX_SHOWN:
        lines.append("... %d additional selected nodes omitted." %
                     (len(node_ids) - MAX_SHOWN))

    mw.message("\n".join(lines))
