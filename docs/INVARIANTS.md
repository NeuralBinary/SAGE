# SAGE invariants

The machine-readable invariant catalog is `spec/invariants.json`. Release qualification maps each invariant to automated tests or conformance checks. An invariant failure blocks release.

Core delivery requires acknowledgement before receiver knowledge changes, deterministic wire identity, explicit failure on authorization or quota boundaries, monotonic ordered-stream sequencing, and deterministic state reconstruction. Semantic optimization must fail open, learned patterns require trust-scoped holdout evidence, and derived information inherits sensitivity. Optional subsystems are isolated from delivery. Codebook releases are signed and Merkle-addressed.


The catalog additionally protects atomic quota fairness, branch-safe checkpoints, trust-scoped holdout promotion, receiver drift demotion, signed deterministic codebook releases, cross-runtime wire identity, and optional-subsystem failure isolation. `python scripts/invariant_check.py` verifies every invariant points to an executable qualification target; release CI executes those targets through the normal test/conformance jobs.
