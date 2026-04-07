#!/usr/bin/env python3
"""
inspect_hits.py  --  Investigate edep-sim photon_hits.root output.

Works with the upstream edep-sim (edep-sim-working) which uses:
  - ev.PhotonDetectors["PhotonDetector"]  (TG4PhotonHit, keyed by SurfaceDetector name)
  - ev.Trajectories                       (TG4Trajectory)
  - ev.Primaries                          (TG4PrimaryVertex)

For each event, prints:
  - Number of photon hits per sensor and total
  - Hit position, start position, photon energy / wavelength, creator process

For each optical photon trajectory (name == "opticalphoton"):
  - Start / end position, displacement, total path length
  - Rayleigh scatter count, boundary-step count
  - End reason: detected / absorbed_bulk / absorbed_wall / escaped_world

Global summary:
  - Hits per event statistics
  - End-reason breakdown
  - Path-length and scatter distributions
  - Diagnosis notes

Usage:
    python3 inspect_hits.py [photon_hits.root] [--max-events N] [--quiet]

Requires: ROOT (via spack environment in .envrc)
"""

import sys
import argparse
import math
import numpy as np
import ROOT

ROOT.gErrorIgnoreLevel = ROOT.kError

# -------------------------------------------------------------------------
# Geant4 process / subprocess codes for optical photons
# From TG4TrajectoryPoint::G4ProcessType / G4ProcessSubtype in TG4Trajectory.h
# -------------------------------------------------------------------------
PROC_TRANSPORTATION = 1
PROC_OPTICAL        = 3

SUB_ABSORPTION   = 31   # G4OpAbsorption  (bulk LAr)
SUB_WLS          = 32   # wavelength shifting
SUB_RAYLEIGH     = 33   # G4OpRayleigh
SUB_BOUNDARY     = 34   # G4OpBoundaryProcess (wall or sensor surface)
SUB_WORLD        = 91   # Transportation: WorldBoundary (escaped)

PROCESS_CREATOR_NAME = {
    0: "Cerenkov",
    2: "Scintillation",
    7: "WLS",
}


def vec3(v):
    return np.array([v.X(), v.Y(), v.Z()], dtype=float)


def classify_photon(traj, detected_ids):
    """Return (end_reason, n_rayleigh, n_boundary, step_lengths, scatter_angles, total_path)."""
    npts = traj.Points.size()
    if npts < 2:
        return "too_short", 0, 0, [], [], 0.0

    points     = [traj.Points[i] for i in range(npts)]
    positions  = [vec3(p.GetPosition()) for p in points]
    procs      = [(p.GetProcess(), p.GetSubprocess()) for p in points]

    # End reason: trust PhotonDetectors over process codes.
    # SurfaceSD records hits at the LAr/SensorMaterial boundary; the photon
    # track then ends (killed by the SD).  Its last trajectory step will show
    # PROC_OPTICAL / SUB_BOUNDARY, which is now unambiguous because we use
    # SensorMaterial (not LiquidArgon) for the sensor volume.
    if traj.GetTrackId() in detected_ids:
        end_reason = "detected"
    else:
        last_p, last_s = procs[-1]
        if last_p == PROC_OPTICAL and last_s == SUB_ABSORPTION:
            end_reason = "absorbed_bulk"
        elif last_p == PROC_OPTICAL and last_s == SUB_BOUNDARY:
            end_reason = "absorbed_wall"
        elif last_p == PROC_TRANSPORTATION and last_s == SUB_WORLD:
            end_reason = "escaped_world"
        else:
            end_reason = f"other(p={last_p},s={last_s})"

    n_rayleigh = 0
    n_boundary = 0
    step_lengths   = []
    scatter_angles = []

    for i in range(1, npts):
        dp = positions[i] - positions[i - 1]
        step_lengths.append(float(np.linalg.norm(dp)))

        p, s = procs[i]
        if p == PROC_OPTICAL and s == SUB_RAYLEIGH:
            n_rayleigh += 1
            if i < npts - 1:
                db = positions[i]   - positions[i - 1]
                da = positions[i+1] - positions[i]
                nb, na = np.linalg.norm(db), np.linalg.norm(da)
                if nb > 0 and na > 0:
                    ct = np.clip(np.dot(db, da) / (nb * na), -1.0, 1.0)
                    scatter_angles.append(math.degrees(math.acos(ct)))
        if p == PROC_OPTICAL and s == SUB_BOUNDARY:
            n_boundary += 1

    total_path = sum(step_lengths)
    return end_reason, n_rayleigh, n_boundary, step_lengths, scatter_angles, total_path


def print_hit_table(sd_name, hits, quiet):
    """Print per-hit details for one sensitive detector."""
    print(f"  [{sd_name}]  {len(hits)} hit(s)")
    if quiet:
        return
    for i, h in enumerate(hits):
        stop  = h.GetStop()
        start = h.GetStart()
        e_eV  = h.GetEnergyDeposit() * 1e6   # MeV → eV
        wl_nm = (1239.84 / e_eV) if e_eV > 0 else 0.0
        proc  = PROCESS_CREATOR_NAME.get(h.GetProcess(), f"proc={h.GetProcess()}")
        print(f"    hit {i:3d}: "
              f"stop=({stop.X():7.1f},{stop.Y():7.1f},{stop.Z():7.1f}) mm  "
              f"E={e_eV:.3f} eV  λ={wl_nm:.1f} nm  "
              f"creator={proc}  primaryId={h.GetPrimaryId()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("rootfile", nargs="?",
                        default="lartpc-geo/photon_hits.root")
    parser.add_argument("--max-events", type=int, default=None,
                        help="Process at most N events")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress per-hit detail lines")
    args = parser.parse_args()

    # Load edepsim I/O library so ROOT can read TG4Event branches
    edep_lib = ("/nfs/data/1/xning/edep-sim-working/edep-sim/install"
                "/lib/libedepsim_io.so")
    if ROOT.gSystem.Load(edep_lib) < 0:
        print(f"WARNING: could not load {edep_lib}")

    f = ROOT.TFile.Open(args.rootfile)
    if not f or f.IsZombie():
        print(f"ERROR: cannot open {args.rootfile}")
        sys.exit(1)

    tree = f.Get("EDepSimEvents")
    if not tree:
        print("ERROR: EDepSimEvents tree not found")
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Print what's actually in the file first
    # -----------------------------------------------------------------------
    print(f"\nFile : {args.rootfile}")
    print(f"Tree : EDepSimEvents  ({tree.GetEntries()} entries)\n")
    tree.GetEntry(0)
    ev0 = tree.Event
    print("First-event structure:")
    print(f"  Primaries      : {ev0.Primaries.size()} vertex/vertices")
    print(f"  Trajectories   : {ev0.Trajectories.size()}")
    print(f"  SegmentDetectors: {list(ev0.SegmentDetectors)}")
    print(f"  PhotonDetectors : {list(ev0.PhotonDetectors)}")
    print()

    n_events = tree.GetEntries()
    if args.max_events:
        n_events = min(n_events, args.max_events)

    # -----------------------------------------------------------------------
    # Accumulators
    # -----------------------------------------------------------------------
    hits_per_event    = []          # total photon hits per event
    all_total_paths   = []
    all_n_rayleigh    = []
    all_step_lengths  = []
    all_scatter_angles= []
    end_counts        = {}

    for ievt in range(n_events):
        tree.GetEntry(ievt)
        ev = tree.Event

        # ------------------------------------------------------------------
        # Photon hits: collect all detected track IDs across all SDs
        # ------------------------------------------------------------------
        detected_ids = set()
        total_hits_this_event = 0
        # Iterate the std::map via its iterator (more reliable in pyROOT
        # than dict(map) which can silently miss entries).
        photon_detectors = ev.PhotonDetectors   # TG4PhotonHitDetectors = std::map

        for item in photon_detectors:
            sd_name = item.first
            hit_vec = item.second
            hits = list(hit_vec)
            total_hits_this_event += len(hits)
            for h in hits:
                pid = h.GetPrimaryId()
                if pid >= 0:
                    detected_ids.add(pid)

        hits_per_event.append(total_hits_this_event)

        print(f"=== Event {ev.EventId}  "
              f"({ev.Trajectories.size()} traj, "
              f"{total_hits_this_event} photon hits) ===")

        # Print primary vertex source position
        if ev.Primaries.size() > 0:
            vtx = ev.Primaries[0]
            vp  = vtx.GetPosition()
            print(f"  Primary vertex: ({vp.X():.1f},{vp.Y():.1f},{vp.Z():.1f}) mm")

        # Print hit tables
        for item in photon_detectors:
            print_hit_table(item.first, list(item.second), args.quiet)

        # ------------------------------------------------------------------
        # Trajectory analysis for optical photons
        # ------------------------------------------------------------------
        n_traj = ev.Trajectories.size()
        for it in range(n_traj):
            traj = ev.Trajectories[it]
            if traj.GetName() != "opticalphoton":
                continue

            end_reason, n_r, n_b, steps, angles, path = \
                classify_photon(traj, detected_ids)

            all_total_paths.append(path)
            all_n_rayleigh.append(n_r)
            all_step_lengths.extend(steps)
            all_scatter_angles.extend(angles)
            end_counts[end_reason] = end_counts.get(end_reason, 0) + 1

            if not args.quiet:
                pts  = traj.Points
                sp   = vec3(pts[0].GetPosition())
                ep   = vec3(pts[pts.size()-1].GetPosition())
                disp = np.linalg.norm(ep - sp)
                mom0 = traj.GetInitialMomentum()
                e_eV = mom0.E() * 1e6
                print(f"  photon tid={traj.GetTrackId():3d}: "
                      f"start=({sp[0]:7.1f},{sp[1]:7.1f},{sp[2]:7.1f}) "
                      f"end=({ep[0]:7.1f},{ep[1]:7.1f},{ep[2]:7.1f}) mm  "
                      f"disp={disp:7.1f} mm  path={path:7.1f} mm  "
                      f"n_ray={n_r}  n_bnd={n_b}  [{end_reason}]  "
                      f"E={e_eV:.3f} eV")
        print()

    # -----------------------------------------------------------------------
    # Global summary
    # -----------------------------------------------------------------------
    n_photons = len(all_total_paths)
    print("=" * 70)
    print(f"SUMMARY  ({n_photons} optical photon tracks,  {n_events} events)")
    print("=" * 70)

    if hits_per_event:
        h = np.array(hits_per_event)
        print(f"\nPhoton hits per event (SurfaceSD detections):")
        print(f"  total   = {h.sum()}")
        print(f"  mean    = {h.mean():.2f}")
        print(f"  median  = {np.median(h):.1f}")
        print(f"  min/max = {h.min()} / {h.max()}")

    if all_total_paths:
        p = np.array(all_total_paths)
        print(f"\nTotal path length per photon (mm):")
        print(f"  mean    = {p.mean():.1f}")
        print(f"  median  = {np.median(p):.1f}")
        print(f"  min/max = {p.min():.1f} / {p.max():.1f}")

    if all_n_rayleigh:
        r = np.array(all_n_rayleigh)
        print(f"\nRayleigh scatters per photon:")
        print(f"  mean    = {r.mean():.1f}")
        print(f"  median  = {np.median(r):.1f}")
        print(f"  min/max = {int(r.min())} / {int(r.max())}")

    if all_step_lengths:
        s = np.array(all_step_lengths)
        print(f"\nStep lengths between saved trajectory points (mm):")
        print(f"  mean    = {s.mean():.1f}   [configured RAYLEIGH = 900 mm]")
        print(f"  median  = {np.median(s):.1f}")
        print(f"  min/max = {s.min():.1f} / {s.max():.1f}")

    if all_scatter_angles:
        a = np.array(all_scatter_angles)
        print(f"\nRayleigh scatter angle (degrees):")
        print(f"  mean    = {a.mean():.1f}")
        print(f"  median  = {np.median(a):.1f}")
        print(f"  min/max = {a.min():.1f} / {a.max():.1f}")

    print(f"\nEnd-reason breakdown ({n_photons} photons):")
    for reason, cnt in sorted(end_counts.items(), key=lambda x: -x[1]):
        pct = 100.0 * cnt / n_photons if n_photons else 0
        print(f"  {reason:<40s} {cnt:5d}  ({pct:.1f}%)")

    # -----------------------------------------------------------------------
    # Diagnosis
    # -----------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("DIAGNOSIS")
    print("=" * 70)

    n_det  = end_counts.get("detected", 0)
    n_esc  = end_counts.get("escaped_world", 0)
    n_abs  = end_counts.get("absorbed_bulk", 0)
    n_wall = end_counts.get("absorbed_wall", 0)
    total  = n_photons or 1

    if n_det == 0 and n_photons > 0:
        print("  *** No photons detected by SurfaceSD.")
        print("      Possible causes:")
        print("      1. /process/optical/boundary/setInvokeSD true missing from macro")
        print("      2. PhotonSensor volume has wrong material (must differ from LAr)")
        print("      3. SurfaceDetector auxtype not read by edep-sim build")
    else:
        print(f"  Detection efficiency : {n_det}/{total} = {100*n_det/total:.1f}%")

    if n_esc > 0:
        print(f"  {n_esc} photon(s) escaped world boundary — consider enlarging world volume")

    if n_abs > 0 and all_step_lengths:
        mfp = np.mean(all_step_lengths)
        print(f"  Bulk absorption: {n_abs} photon(s).  Mean step = {mfp:.0f} mm "
              f"vs RAYLEIGH={900} mm")

    if n_wall > 0:
        print(f"  Wall absorption: {n_wall} photon(s) absorbed at reflective wall boundaries")


if __name__ == "__main__":
    main()
