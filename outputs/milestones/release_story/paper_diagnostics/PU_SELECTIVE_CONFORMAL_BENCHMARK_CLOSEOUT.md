# PU and Selective-Conformal Benchmark Closeout

This supplement adds two concrete baseline families at alpha=0.10 and K=100
for CTC, materials discovery, and iWildCam: a PyTorch nnPU classifier and a
Bao-style post-selection selective conformal adaptation.  The selective
conformal reference follows the post-selection/FCR setting of Bao et al. 2024,
where selected units receive conformal predictions; here it is adapted as a
candidate-release comparator and is explicitly marked as a different target
object rather than a PARC-equivalent theorem.

Outputs:

- `table_pu_selective_conformal_benchmark.csv`
- `table_pu_selective_conformal_benchmark_seed_rows.csv`
- `figure_table2b_baseline_frontier.csv`

Paper wording: use "different target object (concrete demonstration in
Supplement X)".
