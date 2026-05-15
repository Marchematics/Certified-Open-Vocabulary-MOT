# iWildCam Animal-Present Human-Audit Prospective Package

This milestone freezes a prospective ecology-domain audit trial for animal-present camera-trap detections.

Status: `pending_human_audit`.

The package is not a human-audited flagship result yet. Official iWildCam support is used only for proxy planning tables and release-audit target selection. Human FTR and flagship claims require filled `human_*` fields in the calibration and release audit sheets followed by a rerun of the fixed protocol.

Current local source: frozen GroundingDINO-SwinT animal-present candidates. MegaDetector or another domain-specific frozen animal detector remains the preferred source if outputs are made available through the same schema.

Proxy planning summary:

- blocks: 150 camera-location-by-temporal-chunk blocks
- calibration audit template rows: 2000
- release audit template rows: 167
- raw top-K audit template rows: 300
- proxy-only `alpha=0.20, K=25`: 20/20 non-empty, mean release 25.0, official-proxy FTR 0.0
- proxy-only `alpha=0.20, K=50`: 20/20 non-empty, mean release 50.0, official-proxy FTR 0.0
- proxy-only `alpha=0.10`: certified refusal at all planned K values under current resolution
- random-score control: certified refusal at all planned settings

Interpretation: promising audit target, not paper-facing human-audited evidence until human labels are confirmed.
