# CTC Feature Provenance

The learned-hybrid CTC source uses geometry plus local crop appearance features.
The public leakage audit records sequence-disjoint training/evaluation splits,
training-only normalization, no GT identity or official match label in scorer
features, and held-out GT use only after release for FTR evaluation.
