# A3-v4 Formal Public-Label Exclusion Scope

This gate upgrades the 5k MatterGen diagnostic from formula-level pilot filtering to an available-source formal exclusion pass. The formal pass uses WBM/Matbench formula exclusion inherited from the pilot and alex-mp v20 same-formula StructureMatcher checks with `ltol=0.2`, `stol=0.3`, `angle_tol=5`, primitive-cell matching, scaling and supercell attempts. Formula-only hits are tags only and are not treated as structure matches.

Materials Project entries contained in alex-mp and Alexandria entries contained in alex-mp are included through that local public snapshot. No local OQMD, GNoME, AFLOW or NOMAD structure-level index was available for this gate; those missing sources remain scope limitations. The resulting selection is a pre-DFT release-only pilot gate, not completed prospective materials evidence.
