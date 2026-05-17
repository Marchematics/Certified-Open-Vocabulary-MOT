# Materials Prospective Validation Protocol Closeout

Evidence status: protocol feasibility only.

This milestone freezes A1/A2 designs without claiming a completed prospective
materials result. It introduces no new DFT, no new human labels, and no protocol-only positive row is promoted.

## A1 Temporal Split

- Protocol: `A1_temporal_quasi_prospective_materials_split`
- Status: `ready_if_external_label_timestamp_or_release_snapshot_is_supplied`
- Reason: the local WBM summary contains stable-label fields but no
  label-release timestamp column. A real A1 run needs an external release
  snapshot or timestamp table before it can be evaluated.

## A2 Independent DFT Source

- Protocol: `A2_independent_public_DFT_source_cross_validation`
- Status: `protocol_ready_external_mapping_required`
- Reason: an independent public DFT label source must be joined after the
  release decision. The repository does not fabricate independent-source
  labels from WBM summaries.

## A3

A new DFT follow-up pilot remains optional and is not a current submission
gate.
