Purpose: the canonical decision snapshot contract, simulator math, and journal-level error semantics.

Rules:

- Own validation and normalization of dashboard snapshots.
- Own pure simulator math based on saved stake and saved entry quote.
- Require provider-aware ids in the snapshot so later settlement is deterministic.
- Keep this layer persistence-agnostic and UI-agnostic.
