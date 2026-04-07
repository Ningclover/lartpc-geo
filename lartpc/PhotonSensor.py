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
    material         -- volume material             (default "SensorMaterial")
    SurfaceDetector  -- sensitive detector tag      (default "PhotonDetector")
    '''

    def configure(self,
                  dx=Q("25cm"),
                  dy=Q("25cm"),
                  dz=Q("0.5cm"),
                  material="SensorMaterial",
                  SurfaceDetector="PhotonDetector",
                  **kwds):
        self.dx = dx
        self.dy = dy
        self.dz = dz
        self.material = material
        self.SurfaceDetector = SurfaceDetector
        self.otherKeywords = kwds

    def construct(self, geom):
        shape = geom.shapes.Box(self.name + "_shape",
                                self.dx, self.dy, self.dz)

        volume = geom.structure.Volume(self.name + "_LV",
                                       material=self.material,
                                       shape=shape)

        # Register as a SurfaceDetector so edep-sim (upstream) creates an
        # EDepSim::SurfaceSD for this volume.  SurfaceSD fires via
        # G4OpBoundaryProcess when an optical photon crosses the LAr →
        # SensorMaterial interface; it requires:
        #   1. A real optical boundary (sensor material ≠ LAr) -- satisfied by
        #      using SensorMaterial with its own RINDEX.
        #   2. An optical surface with EFFICIENCY>0 so G4OpBoundaryProcess
        #      sets theStatus=Detection and calls InvokeSD.
        #   3. /process/optical/boundary/setInvokeSD true in the run macro.
        #
        # Optical surface: dielectric_metal with EFFICIENCY=1 means every
        # photon that reaches the sensor face is absorbed and detected.
        # REFLECTIVITY=0 ensures no photon is reflected back into the LAr.
        volume.params.append(("OpSurfaceModel",    "glisur"))
        volume.params.append(("OpSurfaceType",     "dielectric_metal"))
        volume.params.append(("OpSurfaceFinish",   "polished"))
        volume.params.append(("OpReflectivity",    "0.0"))
        volume.params.append(("OpEfficiency",      "1.0"))
        volume.params.append(("SurfaceDetector", self.SurfaceDetector))

        # Forward any extra keyword as aux params.
        for n, v in self.otherKeywords.items():
            volume.params.append((n, v))

        self.add_volume(volume)
