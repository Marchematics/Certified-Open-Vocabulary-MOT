# Success Regime Glossary

This glossary standardizes language used in paper-facing documentation and public artifacts.

## Strict Success

A strict success is a predeclared operating point with a conservative risk target, typically `alpha = 0.10`, non-empty certified releases across the required seed criterion, and realized actual or human-audited FTR at or below the target.

Strict rows are the strongest evidence and may support main-text flagship claims when the verification protocol and provenance are complete.

## Operational Success

An operational success uses a predeclared but less stringent operating point, typically `alpha = 0.20`, and demonstrates a useful release/refusal workflow under realistic verification constraints.

Operational rows should be described as operational demonstrations rather than strict-risk flagships.

## Diagnostic Release

A diagnostic release is informative but not primary. It may use a lower capacity, a relaxed endpoint, or a follow-up audit designed to understand where certification becomes feasible.

Diagnostic rows should not be promoted post hoc to primary endpoints.

## Certified Refusal

A certified refusal occurs when PARC releases no candidates because evidence mass, block coverage, finite-resolution limits, or compatibility constraints are insufficient.

Certified refusal is a valid safety outcome, especially when raw release would be risky or unsupported.

## Boundary Diagnostic

A boundary diagnostic identifies why a source or domain cannot support certified release under the stated protocol. Examples include one-sided reliability failures, high null inflation, weak evidence separation, and block coverage failures.

Boundary diagnostics are evidence about the operating envelope, not failed experiments to hide.

## Reporting Rule

Every main table should state whether each row is strict, operational, diagnostic, refusal, or boundary evidence. This keeps claims aligned with the protocol that generated the row.
