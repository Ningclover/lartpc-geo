import gegede.builder
from gegede import Quantity as Q


class Builder(gegede.builder.Builder):
    '''
    Build the cathode plane with an embedded 5x5 array of photon sensors.

    The cathode is a thin flat box (dx x dy x dz) placed at z=0 (the xy
    mid-plane of the detector).  A 5x5 grid of photon sensor tiles is
    embedded into (placed as daughters of) the cathode volume, uniformly
    distributed over its face.

    The cathode material is set to LiquidArgon (same as the world volume)
    so that no optical boundary exists and photons pass through freely.
    To add partial reflection/absorption in future, change the material to
    a distinct one with RINDEX defined and use dielectric_dielectric surface.

    Configuration parameters
    ------------------------
    dx, dy  -- half-widths of the cathode plane  (default 5 m each)
    dz      -- half-thickness                    (default 0.5 cm)
    material -- cathode material                 (default "CathodeMaterial")
    nx, ny  -- number of sensors along x / y     (default 5 each)
    '''

    def configure(self,
                  dx=Q("5m"),
                  dy=Q("5m"),
                  dz=Q("0.5cm"),
                  material="LiquidArgon",
                  nx=5,
                  ny=5,
                  **kwds):
        self.dx = dx
        self.dy = dy
        self.dz = dz
        self.material = material
        self.nx = int(nx)
        self.ny = int(ny)
        self.otherKeywords = kwds

    def construct(self, geom):
        # ----------------------------------------------------------------
        # Cathode mother volume
        # ----------------------------------------------------------------
        shape = geom.shapes.Box(self.name + "_shape",
                                self.dx, self.dy, self.dz)

        volume = geom.structure.Volume(self.name + "_LV",
                                       material=self.material,
                                       shape=shape)


        # Optical surface parameters commented out: cathode is LiquidArgon,
        # same material as the world, so no boundary exists and photons
        # pass through 100% with no reflection or absorption.
        # Uncomment and switch to dielectric_dielectric + distinct material
        # if partial reflection is needed in future.
        # volume.params.append(("OpSurfaceModel",    "unified"))
        # volume.params.append(("OpSurfaceType",     "dielectric_dielectric"))
        # volume.params.append(("OpSurfaceFinish",   "polished"))
        # volume.params.append(("OpReflectivity",    "0.1"))
        # volume.params.append(("OpTransmittance",   "0.9"))

        for n, v in self.otherKeywords.items():
            volume.params.append((n, v))

        # ----------------------------------------------------------------
        # Place the 5x5 sensor array inside the cathode volume.
        #
        # The sensor sub-builder is the first (and only) sub-builder
        # registered in the config file.  All 25 tiles share the same
        # logical volume (one copy) but are given distinct physical
        # placements with unique names and copy numbers.
        #
        # Sensor pitch = cathode half-width * 2 / nx  (full span / count)
        # Sensor centres are spaced uniformly, starting at:
        #   x_start = -(nx-1)/2 * pitch_x
        #   y_start = -(ny-1)/2 * pitch_y
        # ----------------------------------------------------------------
        sensor_builder = self.get_builder()
        sensor_vol = sensor_builder.get_volume()

        # Full cathode dimensions
        full_x = self.dx * 2
        full_y = self.dy * 2

        # Pitch between sensor centres
        pitch_x = full_x / self.nx
        pitch_y = full_y / self.ny

        # Offset of the first sensor centre from the cathode centre
        x0 = -full_x / 2 + pitch_x / 2
        y0 = -full_y / 2 + pitch_y / 2

        copy = 0
        for ix in range(self.nx):
            for iy in range(self.ny):
                cx = x0 + ix * pitch_x
                cy = y0 + iy * pitch_y
                # Sensors sit flush in the cathode plane; z=0 in cathode coords
                cz = Q("0m")

                pname = f"{sensor_builder.name}_ix{ix}_iy{iy}"
                pos = geom.structure.Position(pname + "_pos", cx, cy, cz)
                rot = geom.structure.Rotation(pname + "_rot",
                                              "0deg", "0deg", "0deg")
                place = geom.structure.Placement(pname + "_place",
                                                 volume=sensor_vol.name,
                                                 pos=pos.name,
                                                 rot=rot.name,
                                                 copynumber=copy)
                volume.placements.append(place.name)
                copy += 1

        self.add_volume(volume)
