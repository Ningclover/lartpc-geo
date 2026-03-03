import gegede.builder
from gegede import Quantity as Q


class Builder(gegede.builder.Builder):
    '''
    Build the world volume: a large vacuum box that contains the detector.

    The world volume is slightly larger than the detector so that the
    detector fits cleanly inside.  The first (and only) sub-builder is
    the Detector builder.

    Configuration parameters
    ------------------------
    dx, dy, dz  -- half-dimensions of the world box (default 6 m each)
    material     -- world fill material (default "Vacuum")
    '''

    def configure(self,
                  dx=Q("6m"),
                  dy=Q("6m"),
                  dz=Q("6m"),
                  material="Vacuum",
                  **kwds):
        self.dx = dx
        self.dy = dy
        self.dz = dz
        self.material = material
        self.otherKeywords = kwds

    def construct(self, geom):
        print(f"Constructing world volume '{self.name}'")

        shape = geom.shapes.Box(self.name + "_shape",
                                self.dx, self.dy, self.dz)

        volume = geom.structure.Volume(self.name + "_LV",
                                       material=self.material,
                                       shape=shape)

        for n, v in self.otherKeywords.items():
            volume.params.append((n, v))

        # Place the detector at the centre of the world.
        detector_builder = self.get_builder()
        detector_vol = detector_builder.get_volume()

        pos = geom.structure.Position(detector_builder.name + "_pos",
                                      "0m", "0m", "0m")
        rot = geom.structure.Rotation(detector_builder.name + "_rot",
                                      "0deg", "0deg", "0deg")
        place = geom.structure.Placement(detector_builder.name + "_place",
                                         volume=detector_vol.name,
                                         pos=pos.name,
                                         rot=rot.name)
        volume.placements.append(place.name)

        self.add_volume(volume)
