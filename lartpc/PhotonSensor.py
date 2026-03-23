import gegede.builder
from gegede import Quantity as Q


class Builder(gegede.builder.Builder):
    '''
    Build a single photon sensor tile.

    Each sensor is a thin flat box (dx x dy x dz) made of SensorMaterial.
    The volume is marked as a sensitive detector and its optical surface
    is set to total absorption (modelled by auxilary parameters that the
    Geant4 simulation reads to configure an OpBorderSurface or
    OpSkinSurface with reflectivity=0, efficiency=1).

    Configuration parameters
    ------------------------
    dx, dy  -- half-widths of the sensor face  (default 25 cm each, giving 0.5 m x 0.5 m)
    dz      -- half-thickness of the sensor     (default 0.5 cm, i.e. 1 cm thick)
    material -- volume material                 (default "SensorMaterial")
    SensDet  -- sensitive detector tag          (default "PhotonDetector")
    '''

    def configure(self,
                  dx=Q("25cm"),
                  dy=Q("25cm"),
                  dz=Q("0.5cm"),
                  material="LiquidArgon",
                  SensDet="PhotonDetector",
                  **kwds):
        self.dx = dx
        self.dy = dy
        self.dz = dz
        self.material = material
        self.SensDet = SensDet
        self.otherKeywords = kwds

    def construct(self, geom):
        shape = geom.shapes.Box(self.name + "_shape",
                                self.dx, self.dy, self.dz)

        volume = geom.structure.Volume(self.name + "_LV",
                                       material=self.material,
                                       shape=shape)

        # Mark as sensitive detector so Geant4 registers optical hits here.
        # No optical surface is defined: the sensor material is the same as
        # the surrounding LAr, so photons enter without reflection at the
        # boundary.  Detection (including any QE weighting) is handled
        # entirely in the sensitive detector ProcessHits, matching the
        # approach used in sim_lighttrap.
        volume.params.append(("SensDet", self.SensDet))

        # Forward any extra keyword as aux params.
        for n, v in self.otherKeywords.items():
            volume.params.append((n, v))

        self.add_volume(volume)
