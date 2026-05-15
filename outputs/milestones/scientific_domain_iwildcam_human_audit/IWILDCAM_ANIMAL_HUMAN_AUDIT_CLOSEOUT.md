# iWildCam Animal-Present Prospective Human-Audit Closeout

Status: prepared for prospective human audit.

Paper status: `not_a_human_audited_flagship_until_human_fields_are_confirmed`.

This package freezes a candidate-disjoint ecology-domain trial for animal-present
camera-trap detections. The preferred source is MegaDetector or another frozen
domain-specific animal detector; current local execution used:

`GroundingDINO-SwinT animal-present fallback`

Source note: MegaDetector outputs not found locally; frozen GDINO animal-present source used as fallback

Official labels are used only in proxy planning tables. They must not be
reported as human-audited FTR. The blind calibration and release templates are
the inputs for human review.

Prepared assets:

- calibration audit rows: 2000
- raw top-K audit rows: 300
- release audit template rows: 167
- block definition: camera location x 5 temporal chunks
- blocks: 150

Go/no-go remains pending until human-confirmed calibration and release labels
are supplied and rerun through the same predeclared endpoint hierarchy.
