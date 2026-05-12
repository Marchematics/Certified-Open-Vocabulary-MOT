# Phase4 third-generator matrix v1

OWL-ViT v1 (`google/owlvit-base-patch32`) was added as a third proposal generator and evaluated on 100-video OVT-B/TAO smoke candidate universes. The fixed-M=150 matrix covers alpha={0.10,0.20}, seeds={0,1,2}. This is a diagnostic cross-generator result, not a full-scale main result.

OWLv2 mini-audit summary is included for failure-analysis framing: 96/100 top-150 samples were actually true, 0 false, 4 uncertain under a model-assisted user-review-aware protocol.
