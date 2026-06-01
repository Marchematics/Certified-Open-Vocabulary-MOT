# Phase93 Protocol: CTC Strong-Model Calibration

Inputs:

- Phase81 frozen CTC audit packet registry;
- Phase91 deterministic model-surrogate annotations;
- existing CTC strict human-audit labels.

Procedure:

1. Join Phase81 packet rows to Phase91 labels by `audit_item_id`.
2. Join to existing CTC human labels by `source_audit_id == audit_id`.
3. Treat `same_cell_supported` as model positive, `unsupported` as model
   negative, and `uncertain` as abstention.
4. Report confusion and high-confidence positive calibration against existing
   human labels.

This is retrospective calibration only. It is not external human audit evidence.
