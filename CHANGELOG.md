# Changelog

## AI stable v1.0 - 2026-11-26

- Extract the 42 existing AI conditions from Personal V1.4, preserving order and types.
- No domain additions or removals; no automatic upstream synchronization.
- Add a small offline validator and initial additive configuration builder.
- Runtime import and remote loading require device validation.

## Maintenance V1.6 - 2026-11-26

- Add a manually triggered, read-only upstream candidate review workflow and offline tests.
- No changes to stable AI.list, V1.5 config, rule routing, or publication process.
- Device acceptance and live GitHub Actions execution remain separate checks.

## V1.7 maintenance tools (candidate)

- Add read-only same-repository PR validation for additive AI rule proposals and preserve manual merge authority.
- Pin checkout v7.0.1 (Node.js 24); online validation pending.
- Stable AI.list unchanged; V1.5 device validation remains separate.

## V1.8 maintenance tools (candidate)

- Separate actionable candidates, remembered human decisions and blocked shared roots; reopen on scope/source change, expiry or incomplete sources.
- Add initially empty review ledger and validation for ledger-only PRs; no candidate is pre-approved or pre-rejected.
- Stable AI.list and V1.5 configuration remain unchanged.

## AI ecosystem expansion candidate - 2026-11-26

- Append 42 domain conditions to the original 42; no main configuration, workflow or ledger edits.
- Dedicated vendor namespaces and narrowly scoped service hosts only; sources are recorded beside each rule. Four Google API hosts are community evidence, not confirmed official allowlists.
- Historical ledger entries remain intact; candidates covered by the new list are no longer actionable while covered. Existing five-source workflow is unchanged; expanded providers require periodic manual review of the cited documents.
- Static domain matching checked against supplied V1.5; runtime DNS, IP, authentication, third-party resources, client refresh and stability still require validation.
