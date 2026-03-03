#!/usr/bin/env python
'''
Build the LArTPC optical geometry and export to GDML.

Usage:
    python build_geo.py [output.gdml]

Default output file: lartpc.gdml
'''

import sys
import os

# Make sure the lartpc package is importable from this directory.
sys.path.insert(0, os.path.dirname(__file__))

import gegede.configuration
import gegede.interp
import gegede.builder
import gegede.construct
import gegede.export.gdml as gdml_export

CFG_FILE = os.path.join(os.path.dirname(__file__), "lartpc.cfg")
DEFAULT_OUTPUT = os.path.join(os.path.dirname(__file__), "lartpc.gdml")


def build(cfg_file=CFG_FILE, output=DEFAULT_OUTPUT, world_name="World"):
    print(f"Parsing configuration: {cfg_file}")
    cfg = gegede.configuration.configure([cfg_file])

    print(f"Creating builder hierarchy rooted at '{world_name}'")
    wbuilder = gegede.interp.make_builder(cfg, world_name)
    gegede.builder.configure(wbuilder, cfg)

    print("Constructing geometry...")
    geom = gegede.construct.Geometry()
    gegede.builder.construct(wbuilder, geom)

    # The world builder must produce exactly one top-level volume.
    assert len(wbuilder.volumes) == 1, \
        f"World builder produced {len(wbuilder.volumes)} volumes (expected 1)"
    geom.set_world(wbuilder.get_volume(0))
    print(f"World volume: '{geom.world}'")

    print(f"Exporting GDML to: {output}")
    tree = gdml_export.convert(geom)
    gdml_export.output(tree, output)
    print("Done.")
    return output


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUTPUT
    build(output=out)
