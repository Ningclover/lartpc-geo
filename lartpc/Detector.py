import gegede.builder
from gegede import Quantity as Q

from . import MaterialDefinitions


# Half-thickness of each wall slab (1 mm).  Thin enough to be negligible
# optically but thick enough to be a valid Geant4 volume.
WALL_DZ = Q("1mm")


def _make_wall(geom, name, dx, dy, dz, surface_params):
    '''Helper: create a thin rectangular wall volume with given surface params.'''
    shape  = geom.shapes.Box(name + "_shape", dx, dy, dz)
    volume = geom.structure.Volume(name + "_LV",
                                   material="WallMaterial",
                                   shape=shape)
    for k, v in surface_params:
        volume.params.append((k, v))
    return volume


class Builder(gegede.builder.Builder):
    '''
    Build the main detector volume: a 10 m x 10 m x 10 m box filled with
    liquid argon.

    Six thin wall slabs (1 mm each) line the inside of the LAr box:

      top  / bottom  (±z faces) -- total absorption
                                   (dielectric_metal, glisur, polished, R=0)
      +x / -x / +y / -y faces  -- diffuse ground finish
                                   (dielectric_metal, unified, ground, R=0.x)

    The central cathode plane (with embedded photon sensors) sits at z=0.

    Configuration parameters
    ------------------------
    dx, dy, dz   -- half-dimensions of the LAr box (default 5 m each)
    material     -- fill material (default "LiquidArgon")
    wall_r_side  -- reflectivity of the four side walls (default 0.9)
    '''

    def configure(self,
                  dx=Q("5m"),
                  dy=Q("5m"),
                  dz=Q("5m"),
                  material="LiquidArgon",
                  wall_r_side="0.9",
                  **kwds):
        self.dx = dx
        self.dy = dy
        self.dz = dz
        self.material = material
        self.wall_r_side = str(wall_r_side)
        self.otherKeywords = kwds

    def construct(self, geom):
        MaterialDefinitions.DefineMaterials(geom)

        # ----------------------------------------------------------------
        # Detector mother volume -- liquid argon box
        # No skin surface here; surfaces are on the individual wall slabs.
        # ----------------------------------------------------------------
        shape  = geom.shapes.Box(self.name + "_shape",
                                 self.dx, self.dy, self.dz)
        volume = geom.structure.Volume(self.name + "_LV",
                                       material=self.material,
                                       shape=shape)

        for n, v in self.otherKeywords.items():
            volume.params.append((n, v))

        # ----------------------------------------------------------------
        # Wall surface parameter sets
        # ----------------------------------------------------------------

        # Top / bottom: total absorption
        #   dielectric_metal + glisur + polished, R=0
        abs_params = [
            ("OpSurfaceModel",  "glisur"),
            ("OpSurfaceType",   "dielectric_metal"),
            ("OpSurfaceFinish", "polished"),
            ("OpReflectivity",  "0.0"),
            ("OpEfficiency",    "0.0"),
        ]

        # Four side walls: diffuse ground reflector
        #   dielectric_metal + unified + ground, user-set R
        side_params = [
            ("OpSurfaceModel",  "unified"),
            ("OpSurfaceType",   "dielectric_metal"),
            ("OpSurfaceFinish", "ground"),
            ("OpReflectivity",  self.wall_r_side),
        ]

        # ----------------------------------------------------------------
        # Build and place the 6 wall slabs.
        #
        # Wall half-dimensions:
        #   top/bottom  (z-faces): full xy extent, thickness in z
        #   side walls  (x/y-faces): full span in the perpendicular direction,
        #                            thickness in the normal direction
        #
        # Positions are at ±(detector_half - wall_half) so the slab sits
        # flush against the inner face of the LAr box boundary.
        # ----------------------------------------------------------------
        walls = [
            # name,   dx,          dy,          dz,       pos_x,   pos_y,   pos_z,     params
            ("WallTop",    self.dx,     self.dy,     WALL_DZ,
             Q("0m"), Q("0m"),  self.dz - WALL_DZ,   abs_params),
            ("WallBottom", self.dx,     self.dy,     WALL_DZ,
             Q("0m"), Q("0m"), -(self.dz - WALL_DZ), abs_params),
            ("WallPosX",   WALL_DZ,     self.dy,     self.dz,
              self.dx - WALL_DZ, Q("0m"), Q("0m"),   side_params),
            ("WallNegX",   WALL_DZ,     self.dy,     self.dz,
             -(self.dx - WALL_DZ), Q("0m"), Q("0m"), side_params),
            ("WallPosY",   self.dx,     WALL_DZ,     self.dz,
             Q("0m"),  self.dy - WALL_DZ, Q("0m"),   side_params),
            ("WallNegY",   self.dx,     WALL_DZ,     self.dz,
             Q("0m"), -(self.dy - WALL_DZ), Q("0m"), side_params),
        ]

        for (wname, wdx, wdy, wdz, px, py, pz, wparams) in walls:
            wvol = _make_wall(geom, wname, wdx, wdy, wdz, wparams)
            pos  = geom.structure.Position(wname + "_pos", px, py, pz)
            rot  = geom.structure.Rotation(wname + "_rot",
                                           "0deg", "0deg", "0deg")
            place = geom.structure.Placement(wname + "_place",
                                             volume=wvol.name,
                                             pos=pos.name,
                                             rot=rot.name)
            volume.placements.append(place.name)

        # ----------------------------------------------------------------
        # Place the cathode (with its embedded sensors) at z=0
        # ----------------------------------------------------------------
        cathode_builder = self.get_builder()
        cathode_vol     = cathode_builder.get_volume()

        pos   = geom.structure.Position(cathode_builder.name + "_pos",
                                        "0m", "0m", "0m")
        rot   = geom.structure.Rotation(cathode_builder.name + "_rot",
                                        "0deg", "0deg", "0deg")
        place = geom.structure.Placement(cathode_builder.name + "_place",
                                         volume=cathode_vol.name,
                                         pos=pos.name,
                                         rot=rot.name)
        volume.placements.append(place.name)

        self.add_volume(volume)
