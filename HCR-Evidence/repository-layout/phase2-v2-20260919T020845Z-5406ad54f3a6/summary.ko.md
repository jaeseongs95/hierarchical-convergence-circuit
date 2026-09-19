# Repository root cleanup Phase 2 v2

- status: `APPLIED_AND_VERIFIED`
- HEAD: `83d07f43cb9b138cadfcdbdd1f0e40bcfb5857e9`
- planned assets: 52
- pre-cleanup full regression: **not executed**
- during-cleanup full regression: **not executed**
- final full regression: **one run only**
- R031~R033 launchers: **retained because current tests import them**

## Structural audit

```json
{
  "verified": true,
  "moved_files": 52,
  "bytes_preserved": true,
  "r031_r033_test_launchers_retained": true,
  "r048_r049_contracts_verified": true
}
```

## Final regression

```json
{
  "errors": 0,
  "failures": 0,
  "skipped": [
    {
      "reason": "symlink creation is not available",
      "test": "test_r021_sessions.CheckpointIO.test_file_symlink_rejected"
    },
    {
      "reason": "symlink creation is not available",
      "test": "test_r021_sessions.CheckpointIO.test_symlink_parent_rejected"
    },
    {
      "reason": "local symlink creation not supported",
      "test": "test_r034_selection.ProtocolAndIO.test_symlink_rejected"
    }
  ],
  "tests_run": 602,
  "returncode": 0
}
```
