# SAGE v0.2.7

v0.2.7 is a release-hygiene and licensing release. The SAGE protocol remains `sage/0.2`, wire version `2`; there are no protocol or migration changes.

## Highlights

- Moves the 0.2.7 source line to `AGPL-3.0-or-later` plus separately negotiated commercial licensing while preserving the MIT terms of tagged v0.2.6 and earlier releases.
- Aligns Python, Hermes, OpenClaw, manifests, build scripts, package checks, CI artifact names, and release metadata on package version 0.2.7.
- Adds the SAGE Contributor License Agreement and pull-request acknowledgement needed for third-party contributions to a dual-licensed project.
- Replaces the stale MIT license bundled with the OpenClaw adapter and locks adapter license payloads to the root license.
- Organizes benchmark documentation around evidence type: deterministic Phoenix results, frozen held-out Orion wire measurements, oracle upper bounds, and provider-backed evaluation when available.
- Keeps the public protocol, wire format, TCK vectors, and database migration baseline unchanged.

## Compatibility

SAGE v0.2.7 remains on protocol `sage/0.2` / wire `2`. The licensing and release-metadata changes do not change wire compatibility.

## Verification

The release workflow runs the full Python test suite, strict type checking, coverage, security and architecture gates, Python/JavaScript/Go conformance, differential fuzzing, OpenClaw build/TCK checks, packaged-asset validation, Docker quick-start verification, and staging gates before publishing assets.
