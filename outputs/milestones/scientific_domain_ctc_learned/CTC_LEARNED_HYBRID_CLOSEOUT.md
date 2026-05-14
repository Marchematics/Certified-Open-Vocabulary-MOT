# CTC Learned-Hybrid Closeout

This milestone adds an AI-assisted learned-hybrid CTC proposal source. The scorer is trained on sequence 01, frozen, and evaluated/certified on held-out sequence 02. It uses geometric link features plus local crop appearance statistics and crop-correlation signals; forbidden GT/matching columns are not used as model features.

The main table reports PARC release/refusal under partial verification on the held-out candidate universe. The strict alpha=0.10 rows are a pre-specified small-K sensitivity extension, not an after-the-fact primary-row selector.
