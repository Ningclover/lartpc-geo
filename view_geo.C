void view_geo(const char* gdml = "lartpc.gdml") {
    TGeoManager::SetDefaultUnits(TGeoManager::kG4Units);
    TGeoManager::Import(gdml);

    // SetVisOption(0): draw all nodes (leaves + containers).
    // SetVisOption(1): draw leaves only (ROOT default — why Detector was missing).
//    gGeoManager->SetVisOption(0);
//    gGeoManager->SetVisLevel(6);

    // ---------------------------------------------------------------
    // Set visibility on every volume, then override per-volume below.
    // ---------------------------------------------------------------
    TIter next(gGeoManager->GetListOfVolumes());
    TGeoVolume* v;
    while ((v = (TGeoVolume*)next())) {
        v->SetVisibility(kTRUE);
        v->SetVisDaughters(kTRUE);
    }

    // World: invisible (just the envelope)
    gGeoManager->GetVolume("World_LV")->SetVisibility(kFALSE);

    // Detector: cyan wireframe — SetFillStyle(0) makes it hollow
    TGeoVolume* det = gGeoManager->GetVolume("Detector_LV");
    det->SetLineColor(kCyan+1);
    det->SetLineWidth(2);
    det->SetFillColor(0);
    det->SetFillStyle(0);       // hollow (wireframe)
    det->SetTransparency(90);   // near-transparent fill so daughters show through

    // Cathode: yellow plane
    TGeoVolume* cat = gGeoManager->GetVolume("Cathode_LV");
    cat->SetLineColor(kYellow+1);
    cat->SetFillColor(kYellow-9);
    cat->SetTransparency(30);

    // Sensors: solid red tiles (only present when PhotonSensor is enabled)
    TGeoVolume* sen = gGeoManager->GetVolume("PhotonSensor_LV");
    if (sen) {
        sen->SetLineColor(kRed);
        sen->SetFillColor(kRed);
        sen->SetTransparency(0);
    }

    // Draw from World so the full hierarchy is rendered.
    // "ogl" opens the OpenGL viewer; use "" for the default pad painter.
    TGeoVolume* top = gGeoManager->GetTopVolume();
    top->Draw("ogl");
}
