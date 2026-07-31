# SAGE higher-order patterns

SAGE v0.2 persists higher-order recurring semantic templates in the primary database. SQLite is suitable for local development; PostgreSQL is the production target.

## Storage and graph structure

`pattern_candidates` stores recurring templates below promotion threshold. `learned_patterns` stores promoted shadow/validated/active/cooling/deprecated/retired definitions. `pattern_edges` stores parent→child composition edges for recursive patterns. `pattern_receiver_metrics` stores counterfactual fidelity and outcome evidence per workspace/receiver/model.

Each learned pattern owns an ordinary concept code. The pattern retains a **lossless flattened composition** for matching/fallback even when it also composes child patterns, so recursive learning never makes decoding depend on opaque hidden state.

## Template semantics

Components contain canonical meaning, normalized path shape, literal-presence information, and `none`, `constant`, or typed `slot` literal mode. Strings are slots by default (`SAGE_PATTERN_STRING_CONSTANTS_ENABLED=false`) to avoid accidentally turning names/PII into shared vocabulary.

## Utility-weighted lifecycle

1. `candidate` — accumulates frequency, savings, diversity/stability.
2. `shadow` — concept exists, but packet output is unchanged.
3. `validated` — task feedback is good enough to continue evaluation.
4. `active` — counterfactual full-vs-compressed evidence passes the configured fidelity/outcome gate.
5. `cooling` — insufficient recent utility/use; not emitted.
6. `deprecated` / `retired` — retained for decoding/history, not emitted.

Candidate promotion uses a utility score based on frequency × savings × stability, with configured minimum frequency/savings/utility floors. Active selection additionally accounts for task utility, ambiguity and interoperability.

Counterfactual validation is **required by default**. Receiver/model metrics compare full-task success, compressed-task success and semantic fidelity. A pattern below `SAGE_PATTERN_RECEIVER_MIN_FIDELITY` is not emitted to that receiver/model, even if it remains active elsewhere.

## Namespaces and garbage collection

Namespaces inherit from parents (`software.python.project` → `software.python` → `software`). High-utility patterns can be promoted to a parent namespace; broader promotion is deliberately harder through `SAGE_PATTERN_NAMESPACE_PROMOTION_MIN_UTILITY`.

Garbage collection moves old active patterns to cooling and later retirement. Using a cooling pattern reactivates it.

## Configuration

- `SAGE_PATTERN_LEARNING_ENABLED`
- `SAGE_PATTERN_STRING_CONSTANTS_ENABLED`
- `SAGE_PATTERN_MIN_COMPONENTS`
- `SAGE_PATTERN_MAX_COMPONENTS`
- `SAGE_PATTERN_MAX_OBSERVATIONS_PER_MESSAGE`
- `SAGE_PATTERN_CANDIDATE_MIN_COUNT`
- `SAGE_PATTERN_MIN_SAVINGS_BYTES`
- `SAGE_PATTERN_UTILITY_MIN_SCORE`
- `SAGE_PATTERN_SHADOW_MIN_SAMPLES`
- `SAGE_PATTERN_SHADOW_MIN_SUCCESS`
- `SAGE_PATTERN_AUTO_ACTIVATE`
- `SAGE_PATTERN_COUNTERFACTUAL_REQUIRED` (default `true`)
- `SAGE_PATTERN_COUNTERFACTUAL_MIN_SAMPLES`
- `SAGE_PATTERN_COUNTERFACTUAL_MIN_FIDELITY`
- `SAGE_PATTERN_RECEIVER_MIN_FIDELITY`
- `SAGE_PATTERN_GC_COOLING_DAYS`
- `SAGE_PATTERN_GC_RETIRE_DAYS`
- `SAGE_PATTERN_NAMESPACE_PROMOTION_MIN_UTILITY`

## Source trust and promotion scope

v0.2 records source evidence separately from pattern frequency. Normal sends derive source identity from the authenticated/logical sender; provenance does not create additional source diversity.

Default minimum distinct trusted sources increase by scope:

| Scope | Minimum sources |
| --- | ---: |
| session | 2 |
| project | 3 |
| workspace | 4 |
| domain | 6 |
| federation | 8 |

The thresholds are configurable. Promotion also enforces the dominant-source-share and aggregate trust thresholds, so splitting a high-volume stream across repeated observations from one source cannot create broad vocabulary authority.

## Reliability calibration

Receiver/model/task evidence is bucketed by predicted confidence and observed downstream outcome. SAGE tracks sample count, expected calibration error, Brier score, and a calibrated probability. Pattern selection uses the lower of raw receiver fidelity and calibrated reliability when sufficient evidence exists.

Calibration is evidence for compression policy, not a replacement for the semantic-loss firewall or counterfactual validation.
