##########################################################################
# Material definitions for the LArTPC optical geometry.
#
# Materials defined here:
#   - Elements: Ar, C, H, O, N, Si
#   - LiquidArgon: the active medium with optical properties
#   - Vacuum: near-vacuum for world fill
#   - CathodeMaterial: thin transparent cathode (G10/FR4-like)
#   - SensorMaterial: photon sensor active face (silicon-like)
##########################################################################

def DefineElements(geom):
    '''Define elements needed for this geometry.  Called once.'''
    try:
        DefineElements.Called += 1
        print("DefineElements was called again (skipping).")
        return
    except AttributeError:
        DefineElements.Called = 0

    print("Defining elements...")

    geom.matter.Element("Elem_argon",    "Ar", 18, "39.948*g/mole")
    geom.matter.Element("Elem_carbon",   "C",   6, "12.0107*g/mole")
    geom.matter.Element("Elem_hydrogen", "H",   1, "1.00791*g/mole")
    geom.matter.Element("Elem_oxygen",   "O",   8, "15.999*g/mole")
    geom.matter.Element("Elem_nitrogen", "N",   7, "14.0671*g/mole")
    geom.matter.Element("Elem_silicon",  "Si", 14, "28.0855*g/mole")


def DefineMaterials(geom):
    '''Define all materials for the LArTPC geometry.  Called once.'''
    try:
        DefineMaterials.Called += 1
        print("DefineMaterials was called again (skipping).")
        return
    except AttributeError:
        DefineMaterials.Called = 0

    DefineElements(geom)
    print("Defining materials...")

    # ------------------------------------------------------------------
    # Vacuum -- extremely low density air, used for world volume.
    # Photons traverse this without interaction.
    # ------------------------------------------------------------------
    geom.matter.Mixture("Vacuum",
                        density="1.0E-25*g/cc",
                        components=(("Elem_nitrogen", 0.78),
                                    ("Elem_oxygen",   0.22)))

    # ------------------------------------------------------------------
    # Liquid Argon -- the active detector medium.
    #
    # Optical properties added as material property vectors so that
    # Geant4's optical physics can use them.  The values here are
    # representative for LAr at 87 K.
    #
    # RINDEX: refractive index vs photon energy (eV)
    #   LAr refractive index ≈ 1.232 at 128 nm (9.686 eV)
    #
    # ABSLENGTH: bulk absorption length vs photon energy.
    #   LAr is nearly transparent at its own scintillation wavelength;
    #   we set a very long absorption length (10 m = 1000 cm).
    #
    # RAYLEIGH: Rayleigh scattering length vs photon energy.
    #   For LAr at 128 nm, ~90 cm is a typical value.
    #
    # The property vectors here use the format expected by gegede's
    # GDML exporter: a flat list [E1, val1, E2, val2, ...] stored as
    # a matrix with coldim=2 in the GDML <define> section.
    # ------------------------------------------------------------------
    geom.matter.Mixture("LiquidArgon",
                        density="1.3954*g/cc",
                        components=(("Elem_argon", 1.0),),
                        properties=(
                            # RINDEX: refractive index vs energy (MeV).
                            # Two distinct energy points required by Geant4.
                            # 128 nm = 9.686 eV; bracket with ±0.1 eV.
                            ("RINDEX",    [9.586e-3, 1.232,
                                           9.786e-3, 1.232]),
                            # ABSLENGTH: bulk absorption length in mm.
                            # 10 m = 10000 mm; essentially transparent at 128 nm.
                            ("ABSLENGTH", [9.586e-3, 10000.0,
                                           9.786e-3, 10000.0]),
                            # RAYLEIGH: Rayleigh scattering length in mm.
                            # ~90 cm = 900 mm at 128 nm in LAr.
                            ("RAYLEIGH",  [9.586e-3, 900.0,
                                           9.786e-3, 900.0]),
                        ))

    # ------------------------------------------------------------------
    # Cathode material -- thin (1 cm) central plane.
    # For now treated as transparent (G10/FR4 placeholder).
    # Optical surface set to dielectric_dielectric total transmission
    # via auxiliary params on the volume.
    # ------------------------------------------------------------------
    geom.matter.Molecule("CathodeMaterial",
                         density="1.850*g/cc",
                         elements=(("Elem_carbon",   22),
                                   ("Elem_hydrogen",  5),
                                   ("Elem_oxygen",    4),
                                   ("Elem_nitrogen",  1)))

    # ------------------------------------------------------------------
    # Photon sensor material -- silicon (SiPM-like active face).
    #
    # RINDEX is required so that G4OpBoundaryProcess can compute the
    # LAr → SensorMaterial optical boundary.  Without it, Geant4 aborts
    # with "Material has no refractive index".
    #
    # Silicon refractive index at 128 nm (9.686 eV) is ~1.7 (real part).
    # Two bracketing energy points are required by Geant4.
    # The high index relative to LAr (1.232) means photons are strongly
    # refracted at the boundary; combined with zero reflectivity set on
    # the SurfaceDetector volume (handled by SurfaceSD), all photons
    # that reach the sensor face are recorded as hits.
    # ------------------------------------------------------------------
    geom.matter.Mixture("SensorMaterial",
                        density="2.329*g/cc",
                        components=(("Elem_silicon", 1.0),),
                        properties=(
                            ("RINDEX", [9.586e-3, 1.7,
                                        9.786e-3, 1.7]),
                        ))

    # ------------------------------------------------------------------
    # Wall material -- thin structural walls of the detector vessel.
    # Steel-like; optical surface properties are set per-wall via
    # auxiliary params on the logical volume.
    # ------------------------------------------------------------------
    geom.matter.Mixture("WallMaterial",
                        density="7.874*g/cc",
                        components=(("Elem_carbon", 0.001),
                                    ("Elem_silicon", 0.999)))
