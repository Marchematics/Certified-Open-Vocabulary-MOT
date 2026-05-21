# Data Access Go/No-Go

This milestone preregisters the first week of the materials-label
discordance paper route. It does not claim a new result. It decides whether
the route is worth launching.

## Secret Handling

Materials Project credentials are read only from `MP_API_KEY` in the local
environment. No API key, token, cookie, raw credential or private response
payload may be written to this repository, to any manifest, or to a paper
artifact.

Current environment credential presence recorded by the builder:
`MP_API_KEY present = true`.

Because the key has been shared in conversation, rotate it before using this
milestone for a public or collaborative run.

## Step 0: Data Access Gate

Pass requires two legally accessible public DFT label snapshots plus the
WBM/Matbench benchmark context. The minimal preferred pair is Materials
Project and Alexandria. OQMD may serve as a replication or secondary source,
but a low-coverage exact-match join is not enough by itself.

If this gate fails, the discordance paper route stops. No prose, abstract or
pipeline expansion should continue.

## Step 1: Minimal Discordance Probe

Run exact/high-confidence structure matching between two independent source
snapshots. Formula-only matches are tags only and cannot enter the primary
denominator.

Go: binary stable/unstable discordance is at least 0.40 on at least 200
matched structures with at least 20% pair coverage.

No-go: discordance is at most 0.10, the matched denominator is below 200, or
pair coverage is below 20%.

Boundary: 0.10-0.40 discordance requires a third-source replication before a
paper launch decision.

## Step 2: Downstream Consequence Gate

Discordance alone is not enough for an NMI-scale claim. At least one
downstream conclusion must change: a public-model ranking flips, a discovered
stable-material count changes materially, or a release/refuse probe changes
decision under source A versus source B.

If ranking and discovered counts are stable, the route is downgraded to a
diagnostic note even if Step 1 finds label disagreement.
