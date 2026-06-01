# Phase92 Protocol: GNoME MP Neighbor Gap Analysis

Inputs:

- Phase91 GNoME MP formula prefilter rows.

Procedure:

1. Exclude exact formula candidates; Phase91 found none.
2. Compute fractional-composition L1 distance and site-count ratio for
   chemical-system neighbors.
3. Report best neighbor per GNoME row.
4. Do not fetch structures, run StructureMatcher, or report stability fields.
