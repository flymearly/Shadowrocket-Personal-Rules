# Shadowrocket Personal Rules

A small, independently maintained AI rule library for Shadowrocket. The initial stable list is the exact 42 domain conditions from Personal V1.4, in original order. Only rule conditions are published; no node, subscription, credential, private configuration, or connection logs belong here.

## Stable release

`main:rules/AI.list` is the published list. Review edits before committing/pushing to main. There is no scheduled upstream import or automatic publication. The initial integration is additive: keep the 42 local AI rules and put the remote RULE-SET immediately before YouTube/Google. The separate unchanged V1.4 config is the rollback path. If a remote resource fails to download or compile, local rules do not guarantee successful activation; use V1.4.

## Maintenance

1. Edit `rules/AI.list` after reviewing evidence. Use only DOMAIN or DOMAIN-SUFFIX, followed by the host (no policy column). Prefer exact shared hosts, never wholesale shared provider roots.
2. Run `python3 tools/ai_rules.py validate` and `git diff -- rules/AI.list CHANGELOG.md`. This checks syntax, duplicates, a limited shared-host guard and suffix redundancy, not full routing behavior or service ownership. Review interactions with Google, YouTube, other apps and the local baseline manually. A remote deletion cannot cancel a local baseline rule.
3. Update CHANGELOG.md, commit the reviewed changes and push main. Verify the raw URL returns the published bytes. In Shadowrocket refresh the rules via Use Configuration / Compile Configuration and test. Refresh may also update the pre-existing AppleNews list.
4. Roll back a bad update with `git revert <commit>` then push and refresh, or immediately activate the unchanged V1.4 config. Never force-push.

## Initial config generation

After creating a PUBLIC GitHub repository named `Shadowrocket-Personal-Rules` and pushing main, fetch the raw list anonymously and compare it with `rules/AI.list`. Run:

```
python3 tools/ai_rules.py build --base /path/to/Shadowrocket-Personal-V1.4.conf --remote-list /path/to/downloaded-AI.list --owner YOUR_GITHUB_LOGIN --output /path/to/Shadowrocket-Personal-V1.5.conf
```

The builder is only for the initial migration: it requires the exact V1.4 SHA-256, exact initial 42-rule sequence and exact downloaded bytes; it refuses to overwrite the output. It adds one RULE-SET and explanatory comment, without modifying the original lines. Future rule additions do not require rebuilding this config.

## Boundaries

The initial list is inherited, not an exhaustive service inventory. Shared authentication hosts may affect other applications. Neither the validator nor the builder is a Shadowrocket parser or runtime test. Do not commit personal config files or tokens. Do not change DNS, IP rules, keywords, other policy groups or FINAL as part of AI updates.

## V1.6: manual upstream review

Open Actions > Check AI rule updates > Run workflow on main. Read the run summary. The workflow has read-only repository permissions, no schedule, and never edits AI.list. It checks community OpenAI/Gemini/Claude lists, v2fly Google DeepMind and the official OpenRouter developer page (known namespace only). It ignores unsupported syntax including IP/keyword rules, distinguishes covered conditions, shared roots, expansions and other review candidates, and records source hashes. A failed source makes the run incomplete. No upstream absence implies deletion. No candidate is approved automatically. The source lists can be stale or contain other services; consult official documentation and device logs. To publish a selected entry, manually edit AI.list and CHANGELOG.md and use the existing maintenance process. Device acceptance of V1.5 remains separate.

Local offline tests: `python3 -m unittest discover -s tools -p 'test_check_ai_updates.py' -v`.
Local online review: `python3 tools/check_ai_updates.py`.

## V1.7: browser-based proposal review

After a successful upstream check, open `rules/AI.list` on GitHub, edit it and append only individually reviewed conditions. Choose a new branch and create a pull request into main. The same-repository `Validate AI rule proposal` workflow checks that existing conditions are retained in order, new conditions pass the validator, and only AI.list and optionally CHANGELOG.md are changed. In the PR description record the source, reason, affected routing and test plan. Review Files changed and wait for the validation check, then manually merge only if appropriate. No workflow has repository write access. The check is advisory until a required-status-check ruleset is configured; never bypass it or merge third-party proposals without review. This additive workflow does not support removal, scope expansion of existing exact rules, or rollback; those require a separately reviewed change. A PR check is not a runtime test. After merge, verify the raw rule file and refresh Shadowrocket. Keep V1.4 available for fallback. To synchronize the local Mac clone after browser merges, use `git pull --ff-only` from a clean main branch.

## V1.8: review memory

`rules/AI.review.json` starts empty: no previous candidate is presumed approved or rejected. To record a human decision, edit this JSON array in a same-repository PR, using exact condition, risk and source names from the latest successful run. Example (illustrative only, not a real approved entry):

```json
[
  {
    "condition": "DOMAIN,example.googleapis.com",
    "decision": "deferred",
    "risk": "REVIEW_SHARED_OR_NEW_SERVICE",
    "sources": ["Gemini v2fly"],
    "review_until": "2027-02-01",
    "reason": "Await evidence that this is required for a service I use"
  }
]
```

Use `rejected` or `deferred`, with a reason and an ISO UTC review date. A decision only matches the exact condition, source set and risk; it reopens on change, on/after the date, or when any source is incomplete. Previously reviewed entries remain visible in a separate table, not deleted or approved. Blocked roots always appear separately. Entries no longer observed remain in the ledger; remove or revise them explicitly. Accepted rules belong in AI.list, not the ledger. The tool does not track historical upstream snapshots or identify whether an unreviewed candidate is actually new upstream, and changes within a source that do not alter the reported condition/source set/risk do not automatically reopen a decision; use the expiry and source hashes for review. Neither workflow writes the ledger or stable list. Ledger-only PRs and additive AI PRs are validated; checks remain advisory unless branch protection is configured. Never put private logs or credentials in this public ledger.
