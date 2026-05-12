# IJCV BURST OWLv2 Stress v1

- Dataset: BURST val scaffold, 988 videos.
- Proposal generator: OWLv2 HF (`google/owlv2-base-patch16-ensemble`).
- Execution: four-way sharded run, one A10G per shard via `CUDA_VISIBLE_DEVICES`.
- Candidate universe: represented by hashes only; raw frames, raw annotations, model weights, HF cache, and candidate caches are excluded.
- Protocol: fixed global M=150, alpha1 in {0.10, 0.20}, seeds {0,1,2}.
- Result: all PARC full rows are empty; Prop.5 high-evidence mass diagnostic predicts all six empty rows correctly.
- Intended use: cross-generator failure/stress analysis, not main positive result.
