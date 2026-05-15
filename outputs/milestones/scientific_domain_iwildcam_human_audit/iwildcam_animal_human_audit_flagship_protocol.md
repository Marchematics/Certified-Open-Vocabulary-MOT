# iWildCam Animal-Present Prospective Human-Audit Flagship Protocol

## Status and scope

This protocol defines a prospective ecology-domain release trial for PARC. The goal is to test whether real human partial verification can support certified release of animal-present camera-trap detections. It must not be conflated with earlier iWildCam species-prompt or official-proxy diagnostics.

Primary source preference is a frozen domain-specific animal detector such as MegaDetector. If such outputs are unavailable locally, the protocol permits a frozen GroundingDINO animal-present candidate universe as a fallback source. The fallback is explicitly marked as an AI proposal source for prospective audit scaffolding, not as a MegaDetector result.

## Target

- Dataset: iWildCam / camera-trap subset.
- Release unit: one animal-present detection candidate in one image.
- Label space for human verification: `animal`, `not_animal`, `uncertain`.
- One-sided positive rule: only consensus or adjudicated `animal` labels enter PARC as verified positives. `not_animal`, `uncertain`, and disagreement remain unverified and are never used as trusted negatives.

## Blocks

The primary block is `camera location x temporal chunk`. Images within each camera location are ordered chronologically when metadata are available; otherwise image identifiers provide a deterministic ordering. Each location is split into five chronological chunks by default. This gives roughly 150 blocks for the current 30-location subset while preserving camera-dependence structure.

## Prospective audit sets

All audit sets must be disjoint from earlier iWildCam audits and from one another by `path_id`.

1. Calibration audit: 1,500 to 2,000 block-balanced high-score candidate boxes. Human-confirmed animal detections become observed positives for PARC.
2. Release audit: after PARC runs, audit all unique released candidates if at most 300; otherwise audit 300 unique released candidates stratified by block and seed.
3. Raw top-K audit: 200 to 300 raw top-K candidates from the same frozen source for context.

Annotators are blinded to score, official support, method condition, release status, and seed wherever visual tooling permits. Public tables may contain candidate identifiers and source metadata, but not raw images.

## Predeclared endpoints

The hierarchy is fixed before human labels are inspected:

1. Strict endpoint: `K=50`, `alpha=0.10`, pass if non-empty seeds >= 18/20, human FTR <= 0.10, conservative human FTR <= 0.10, and mean release >= 25.
2. Operational endpoint: `K=50` or `K=100`, `alpha=0.20`, pass if non-empty seeds >= 18/20, human FTR <= 0.20, conservative human FTR <= 0.20, and mean release >= 25 for K=50 or >= 50 for K=100.
3. Diagnostic lower-volume endpoint: `K=25`, `alpha in {0.10,0.20}`. Passing this endpoint may be reported as a diagnostic low-volume row, not as the second flagship.

If no endpoint passes, the result is frozen as a prospective no-go and must not be promoted post hoc.

## Controls

- Random-score control: destroy the detector ranking while preserving candidates and labels. PARC should refuse when evidence mass is insufficient.
- Species-prompt contrast: earlier species-level iWildCam results remain a semantic one-sided reliability failure diagnostic.
- Official-proxy contrast: earlier animal-present official-proxy results remain an evidence-mass failure diagnostic.

## Paper-facing rule

Only human-confirmed audit fields can support human FTR or a flagship claim. Official labels may be used only for planning/proxy diagnostics and must be labeled `proxy_planning_only_requires_human_confirmation`.
