# Local documentation verification

Use a clean committed checkout of the exact proposed or merged commit, with Python3 and Git:

```sh
python3 scripts/verify-local.py --base FULL_TARGET_BASE_SHA --receipt-dir /absolute/external/new-receipt-directory
python3 scripts/validate-local-receipt.py /absolute/external/new-receipt-directory/receipt.json
```

The original applicable reusable job checks that `CLAUDE.md` and `CHANGELOG.md` exist. The local command executes both checks and additionally rejects empty or symlinked documents. Both documents already exist at the migration baseline. No documentation is generated, modified, committed or pushed by verification. The reusable workflow's optional auto-generation feature is retained for compatibility, but this repository's manual-only caller explicitly sets `auto_create:false` and uses its own reusable workflow at the same revision, replacing the former personal-account `@main` reference.

Local receipts bind repository, exact HEAD, target-anchored nonempty base diff, command, tool versions, exit status and log hashes. The validator rejects stale, missing, incomplete or altered evidence. Attach local evidence and obtain fresh different-family review before a normal PR merge. Do not fabricate a hosted status or use administrator bypass. Hosted workflow runs consume compute and must not be dispatched as part of this migration. Repository Actions settings are unchanged; automatic push and pull-request triggers are retired.

This is a source/toolkit change with no application runtime upload. Merge rollback is a normal revert PR for the exact squash commit, with the same local check and fresh review. No deployment, client message, credential lookup, DNS, billing or service creation runs here.
