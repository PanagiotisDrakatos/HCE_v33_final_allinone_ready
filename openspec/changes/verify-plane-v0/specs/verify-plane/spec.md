## Purpose

The verify-plane gives an agent or a human one deterministic way to prove that a change actually works against real dependencies, and binds that proof to the exact source tree so a stale or forged result cannot pass as a fresh one.

## ADDED Requirements

### Requirement: Deterministic verification interface

The system SHALL expose a single verification entry point that runs the same checks locally, in a pre-push hook, and in CI, and reports one machine-readable verdict per run drawn from PASS, FAIL, or INCONCLUSIVE.

#### Scenario: A check that produces no output is inconclusive, never a pass
- **WHEN** a required check runs but produces no parseable result (a test run collects zero tests, or a step emits no verdict)
- **THEN** the aggregate verdict SHALL be INCONCLUSIVE and SHALL NOT be PASS

#### Scenario: The verdict is the worst of its parts
- **WHEN** one check is FAIL, another INCONCLUSIVE, and the rest PASS
- **THEN** the aggregate verdict SHALL be FAIL

### Requirement: Content-addressed evidence receipt

The system SHALL write a receipt that records the source tree hash, the diff hash, an inputs digest, the tool versions, the runtime health, the per-check results, and the verified features. The receipt SHALL be treated as valid for a change only when its tree hash equals the current source tree.

#### Scenario: A stale receipt does not make a new change green
- **WHEN** a source file changes after a PASS receipt was written
- **THEN** re-checking the receipt SHALL fail with a stale-receipt error and SHALL NOT report PASS

#### Scenario: A missing receipt is a failure, not an absence
- **WHEN** a required receipt is absent for a run that was expected to produce one
- **THEN** the verdict SHALL be FAIL

### Requirement: Runtime proof against real dependencies

The system SHALL prove at least one real feature by launching the feature's real dependency, exercising the feature, and reading the resulting state back from that dependency. Observing the application's own success output SHALL NOT by itself count as proof.

#### Scenario: A silent write failure is caught by reading back
- **WHEN** the application reports success but the dependency holds none of the expected rows
- **THEN** the runtime proof SHALL be FAIL

#### Scenario: An unhealthy dependency is not proof
- **WHEN** the dependency container starts but never becomes healthy within the wait budget
- **THEN** the runtime proof SHALL be FAIL or INCONCLUSIVE and SHALL NOT be PASS

### Requirement: Honest write path

The backtest run SHALL surface lost batches to its caller. A run that fails to persist a batch after its retry budget, or drops a batch because a queue was full, SHALL exit with a non-zero status.

#### Scenario: Lost batch fails the run
- **WHEN** a batch cannot be written after all retries or is dropped
- **THEN** the run SHALL exit non-zero and name the affected metric

### Requirement: No host-global destruction on the verification path

The verification and cleanup paths SHALL scope container teardown to their own project. The tracked tree SHALL NOT contain a host-global container prune or a bulk removal of all containers reachable from an ordinary developer, CI, or agent command.

#### Scenario: Host-global cleanup is rejected
- **WHEN** a tracked script, Makefile, workflow, or agent prompt contains a host-global container prune or a bulk `rm`/`stop` of every container
- **THEN** the policy check SHALL fail

#### Scenario: Project-scoped cleanup is allowed
- **WHEN** cleanup removes only the verification project's own containers and volumes
- **THEN** the policy check SHALL pass

### Requirement: Single required merge gate

Merge readiness SHALL depend on one required aggregate check that passes only when every verification lane succeeded and the receipt is PASS, schema-valid, and bound to the tree being merged. A skipped, cancelled, or failed lane SHALL NOT read as success.

#### Scenario: A skipped lane does not pass the gate
- **WHEN** a required lane is skipped by a condition or filter
- **THEN** the aggregate gate SHALL fail

#### Scenario: A receipt bound to a different tree does not pass the gate
- **WHEN** the receipt's tree hash does not equal the tree of the commit being merged
- **THEN** the aggregate gate SHALL fail
