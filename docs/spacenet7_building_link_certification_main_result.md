# SpaceNet 7 Building-Link Certification

SpaceNet 7 provides the Earth-observation scientific-domain companion to the
CTC cell-link result. We use the public `labels_match` building footprints to
construct adjacent-month candidate links: a candidate is correct when the same
SpaceNet building identifier persists from month `t` to month `t+1`.

The current pilot uses 18 AOIs, 6,341,788 candidate links, 2,050,769
GT-supported same-building links, and 138 AOI-time blocks. SpaceNet 7
`labels_match` is the single official GT source. The partial-verification
sweep hides most same-building links from PARC and uses the full official GT
only afterward for actual-FTR measurement. Rows with `rho=1.0` are
full-verification/oracle diagnostics, not independent-source validation. Raw
SpaceNet imagery, raw annotations, and the multi-GB candidate universe are not
redistributed; the public milestone contains only summary tables, sweep
diagnostics, figures, and sanitized provenance.

## Main Finding

At `alpha=0.20`, the geometry-linker source is a positive scientific-domain
anchor under the partial-verification protocol. The same aggregate numbers are
observed for the tested `rho` values because the high-score verified-positive
subset already removes the relevant high-evidence positives from the null
superset:

- `M=100`: 17/20 seeds non-empty, mean release 81.75, mean actual FTR 0.003.
- `M=300`: 11/20 seeds non-empty, mean release 165.0, mean actual FTR 0.00233.
- `M=500`: 10/20 seeds non-empty, mean release 240.35, mean actual FTR 0.00136.
- `M=5000`: PARC refuses, with mass ratio 0.263.

The high-volume request is not unsafe under the geometry linker itself; the
geometry ranking is very clean. To test unsafe-generator behavior, we include a
randomized-linker stress variant over the same candidate universe. Its raw
top-M false-link rates are about 66--68%, and PARC releases zero links for all
tested budgets.

## Paper Positioning

Use SpaceNet 7 as the second positive scientific-domain application:
biomedical microscopy in CTC and Earth-observation urban monitoring in
SpaceNet. The randomized-linker variant should be framed as safe refusal under
an intentionally degraded source, not as a failed SpaceNet application.
