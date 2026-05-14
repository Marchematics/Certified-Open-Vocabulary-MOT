# Circularity Check and Paper Outline

## Direct Answer

For both CTC and SpaceNet 7, the verified-positive construction and final FTR
evaluation are derived from the same official ground-truth source:

- CTC: CTC `GT/TRA` tracking truth.
- SpaceNet 7: `labels_match` building identifiers.

Therefore, if the question is literally whether they use the same GT source,
the answer is **yes**.

However, the partial-verification sweeps split that same source into two
roles:

1. PARC sees only an observed-positive subset as verified positives.
2. Hidden GT positives are treated as unsupported/null from PARC's perspective.
3. Full GT is used afterward only to measure actual FTR.

So the right paper-facing framing is:

> Same official GT source, but label-level holdout in the partial-verification
> protocol. `rho=1.0` rows are full-verification/oracle diagnostics, not the
> anti-circularity evidence.

This is **not** an independent-source validation. It is a controlled
partial-verification validation using withheld labels from the same public
ground-truth source.

## Script Evidence

### CTC

`scripts/run_ctc_partial_verification_sweep.py` constructs:

- `_full_false = is_unmatched`
- `_full_true = ~_full_false`
- `_observed_positive = observed_true_mask(_full_true, score, rho, seed, strategy)`
- `_partial_null = ~_observed_positive`

Calibration uses `_partial_null`; final actual FTR uses `_full_false`.

This means:

- `rho < 1`: PARC calibration sees only a subset of GT positives; evaluation
  uses held-out/full GT labels.
- `rho = 1`: PARC sees all GT positives; this is circular if presented as a
  real partial-verification result.

### SpaceNet 7

`scripts/prepare_spacenet7_building_link_universe.py` sets:

- `is_unmatched = source_building_id != target_building_id`

`scripts/run_spacenet7_building_link_sweep_fast.py` then constructs:

- `full_false = is_unmatched`
- `full_true = ~full_false`
- `observed = observed_true_mask(full_true, score, rho, seed, strategy)`
- `partial_null = ~observed`

Calibration uses `partial_null`; final actual FTR uses `full_false`.

This has the same status as CTC: label-level holdout from a single official GT
source, not independent-source validation.

## Paper-Facing Rule

Use the following hierarchy in the paper:

1. **Main scientific-domain evidence:** partial-verification rows with
   `rho < 1`, especially the smallest stable observed-positive fraction.
2. **Oracle/full-verification diagnostic:** `rho = 1` rows. Useful for
   explaining the upper envelope of power, but not the main validity evidence.
3. **Independent-source validation:** not currently available for CTC or
   SpaceNet 7.

## iWildCam Narrative Decision

Use iWildCam as a main boundary finding, not as a positive application.

Recommended framing:

> PARC empirically characterizes where release-time guarantees become
> uncertifiable in ecological camera-trap deployment. Species-level prompting
> violates one-sided reliability through semantic misgrounding; animal-present
> prompting repairs the semantic target but lacks sufficient evidence mass.

This should be a Results section, but not the headline positive result. It is
valuable because it shows two distinct failure modes:

- assumption failure: one-sided verified positives are not reliable;
- power failure: verified positives are semantically valid but insufficiently
  high-evidence for certification.

## Proposed NMI Results Structure

### Result 1: Biomedical Cell-Link Certification

Main claim: PARC certifies low-error cell-link releases in CTC under partial
verification.

Evidence:

- four 2D CTC datasets;
- partial-verification `rho < 1` rows as main validity evidence;
- `rho=1` rows only as full-verification/oracle diagnostic;
- unsafe high-volume `M=5000` refusal compared with raw top-M.

### Result 2: Earth-Observation Building-Link Certification

Main claim: the same release-time certification abstraction applies to
SpaceNet 7 building persistence links.

Evidence:

- 18 AOIs, 6.34M candidate links, 138 AOI-time blocks;
- geometry linker as positive Earth-observation source;
- randomized-linker stress as unsafe-generator refusal;
- `rho < 1` rows as main evidence, `rho=1` as diagnostic.

### Result 3: Open-Vocabulary Vision Benchmarks

Main claim: OVT-B, TAO, BURST, LVIS, and black-box generators show that PARC is
not tied to one candidate generator or benchmark.

Evidence:

- OVT-B/TAO/BURST tracking and detection generality tables;
- safe release where high-evidence mass exists;
- certified refusal for weak generators.

### Result 4: Boundary Diagnostics in Ecological Monitoring

Main claim: PARC identifies when a scientific deployment cannot be safely
certified.

Evidence:

- iWildCam species-level semantic mismatch;
- iWildCam animal-present evidence-mass failure;
- do not frame iWildCam as a positive application.

### Result 5: Reliability, Audit, and Reproducibility

Main claim: the certification pipeline is auditable and reproducible.

Evidence:

- Audit2000;
- independent/blind review agreement;
- manifest-hashed public artifacts;
- public-safe benchmark package;
- tests and tiny fixtures.

## Immediate Cleanup Needed

- Revise CTC and SpaceNet docs so the main text emphasizes `rho < 1` rows.
- Label `rho=1` rows as oracle/full-verification diagnostics.
- Avoid saying "independent evaluation source" for CTC or SpaceNet 7.
- Keep all new experiments paused until the paper outline is stabilized.

