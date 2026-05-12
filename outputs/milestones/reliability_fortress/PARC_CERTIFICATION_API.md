# PARC Certification API

Minimum public interface for any tracker/proposal generator:

1. Export `candidate_universe.csv` with one row per path.
2. Export `candidate_nodes.csv` with boxes or masks per path/frame.
3. Optionally export `audit_labels.csv` for one-sided verified positives.
4. Run PARC certification to obtain e-values, SCS releases, risk tables, and audit exports.

Scores are calibrated independently per generator; raw scores are never compared across generators.
