# Refusal Diagnosis and ILP Feasibility Closeout

This diagnostic covers completed refusal rows only. It does not fabricate candidate compatibility graphs. Rows with `max_e < required_e` or `evidence_mass_phi < 1` are infeasible before graph compatibility, so a graph-level ILP cannot rescue them. Rows that are pre-graph feasible but greedy-empty are marked as requiring a candidate graph for a true ILP oracle.

- Diagnosed rows: 4
- Pre-graph finite-resolution or mass failures: 4
- Selector-power limitation is reserved for rows where aggregate evidence is sufficient but SCS-Greedy is empty.
