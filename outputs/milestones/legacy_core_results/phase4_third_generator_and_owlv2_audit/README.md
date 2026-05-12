# Phase4 third generator + OWLv2 mini-audit v1

- OWLv2 top-150 mini-audit completed with a model-assisted, user-review-aware protocol.
- Summary: 96/100 actually_true, 0/100 actually_false, 4/100 uncertain; 96/100 verified-positive for calibration-grade diagnostics.
- OWL-ViT v1 (`google/owlvit-base-patch32`) backend added and smoke proposal generation completed on OVT-B and TAO, 100 videos each.
- OVT-B OWL-ViT smoke: 3017 frame detections, 1876 linked paths, 526 unmatched paths, 300 exported candidates.
- TAO OWL-ViT smoke: 1248 frame detections, 862 linked paths, 563 unmatched paths, 300 exported candidates.

Audit note: small/low-resolution objects were accepted when visually plausible under user prior raw-data review; visually unsupported cases remain `uncertain` and are not calibration verified.
