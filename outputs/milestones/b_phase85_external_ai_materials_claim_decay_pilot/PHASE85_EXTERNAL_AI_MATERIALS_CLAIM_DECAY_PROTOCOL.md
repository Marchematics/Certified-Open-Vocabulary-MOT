# Phase85 External AI-Materials Claim-Decay Audit Pilot

Status: `protocol_frozen_current_reference_verdicts_pending`.

Objective:

Audit whether public AI/materials stability claims remain stable under a
frozen current-reference check, without running new DFT and without changing
the A-paper PARC claim hierarchy.

Primary pilot sources:

- Matbench Discovery / WBM public claim surface;
- GNoME public stable-materials claim surface;
- Alexandria as a third open hull/claim source when available.

Current-reference sources:

- Materials Project current version;
- OQMD current reference.

Primary metrics:

- SCDR: stable-claim decay rate;
- TDB@100: top-100 decay burden;
- EDMB: excess decay over matched background.

Strong pilot gate:

```text
SCDR 95% lower bound > 10%
EDMB 95% lower bound > 3 percentage points
at least two primary sources reproduce a positive decay signal
CAR < 15%
```

No-go gate:

```text
SCDR 95% upper bound < 10%
or leave-one-source-out removes the effect
or CAR > 20%
or structure-level claims cannot be mapped reproducibly
```

Current allowed claim:

Phase85 freezes a B-line external claim-decay audit pilot protocol.  No
current-reference verdicts have been produced.

Forbidden current claims:

- public AI materials claims decay at any particular rate;
- GNoME, Matbench Discovery or Alexandria claims fail current references;
- prospective discovery;
- new DFT evidence;
- independent validation of PARC;
- an A-paper main result.

Evidence scope: `b_line_external_ai_materials_claim_decay_pilot;protocol_frozen;current_reference_verdicts_pending;not_completed_positive_evidence;not_A_paper_main_evidence;not_prospective_discovery;not_new_DFT_evidence`.
