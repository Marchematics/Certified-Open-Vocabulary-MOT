# TrackEval v1

Frozen on 2026-05-09.

This milestone contains MOTChallenge-format TrackEval outputs for PARC-Track and confidence top-M on:

- OVT-B full processed test split, class-agnostic MOTChallenge export.
- TAO supported-subset scaffold, where GT is restricted to categories present in exported predictions to avoid treating federated/unlabeled categories as dense negatives.

Metrics include HOTA, DetA, AssA, LocA, CLEAR MOTA/MOTP/IDSW, and Identity IDF1/IDP/IDR as returned by TrackEval. Raw expanded MOTChallenge files are not retained; manifests record the export parameters and row counts.

Verification: `pytest -q <PARC_ROOT>/tests` -> 45 passed, 1 warning.
