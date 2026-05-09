# ijcv_burst_v2

- Dataset: BURST val box-level scaffold converted from official RLE masks.
- Proposal generator: GroundingDINO scaffold, 8 frames/video, 3 classes/video.
- Proposal execution: four-way sharded run with `video_stride=4`, one process per A10G via `CUDA_VISIBLE_DEVICES`.
- Environment note: GroundingDINO `_C` was rebuilt with `TORCH_CUDA_ARCH_LIST=8.6` for A10G compatibility.
- Main protocol: fixed global `M=150`, `alpha1 in {0.10, 0.20}`, seeds `{0,1,2}`.
- Audit status: 200 model-assisted visual audit labels are included; all released-unsupported paths are covered by the release audit table.
- Candidate universe CSVs are represented by hashes to avoid packaging large derived files.
- Raw frames, raw BURST annotations, model weights, HF/GroundingDINO caches are excluded.
