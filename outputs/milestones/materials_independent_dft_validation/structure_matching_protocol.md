# Structure Matching Protocol

Primary A2 matching requires exact reduced formula plus pymatgen `StructureMatcher` fit with `ltol=0.2`, `stol=0.3`, `angle_tol=5`, `primitive_cell=True`, `scale=True`, and `attempt_supercell=True`. Formula-only OQMD hits are sensitivity diagnostics and do not enter independent FTR.
