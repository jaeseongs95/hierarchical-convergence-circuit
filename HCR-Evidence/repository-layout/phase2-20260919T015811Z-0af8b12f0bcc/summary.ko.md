# Repository root cleanup Phase 2

- status: `FAILED`
- HEAD: `83d07f43cb9b138cadfcdbdd1f0e40bcfb5857e9`
- planned/moved candidates: 55
- pre-cleanup full regression: **not executed**
- during-cleanup full regression: **not executed**
- final full regression: **exactly one run when changes were applied**
- current R048/R049 release contracts: preserved

## Structural audit

```json
{
  "verified": true,
  "moved_files": 55,
  "root_candidates_remaining": 0,
  "current_r048_contract_verified": true,
  "current_r049_contract_verified": true,
  "bytes_preserved": true
}
```

## Final regression

```json
{
  "errors": 6,
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
  "returncode": 2
}
```

## Rollback

```json
{
  "restored": [
    "Run-HCR-R047.py",
    "Run-HCR-R047.cmd",
    "Run-HCR-R046.py",
    "Run-HCR-R046.cmd",
    "Run-HCR-R045.py",
    "Run-HCR-R045.cmd",
    "Run-HCR-R044.py",
    "Run-HCR-R044.cmd",
    "Run-HCR-R043.py",
    "Run-HCR-R043.cmd",
    "Run-HCR-R042.py",
    "Run-HCR-R042.bat",
    "Run-HCR-R041.py",
    "Run-HCR-R041.bat",
    "Run-HCR-R040.py",
    "Run-HCR-R040.bat",
    "Run-HCR-R039.py",
    "Run-HCR-R039.bat",
    "Run-HCR-R038.py",
    "Run-HCR-R038.bat",
    "Run-HCR-R037.py",
    "Run-HCR-R036.py",
    "Run-HCR-R035.py",
    "Run-HCR-R034.py",
    "Run-HCR-R033.py",
    "Run-HCR-R032.py",
    "Run-HCR-R031.py",
    "R047_README.ko.md",
    "R047_MANIFEST.json",
    "R046_README.ko.md",
    "R046_MANIFEST.json",
    "R045_README.ko.md",
    "R045_MANIFEST.json",
    "R044_README.ko.md",
    "R044_MANIFEST.json",
    "R043_README.ko.md",
    "R043_MANIFEST.json",
    "R042_README.ko.md",
    "R042_MANIFEST.json",
    "R041_README.ko.md",
    "R041_MANIFEST.json",
    "R040_README.ko.md",
    "R040_MANIFEST.json",
    "R039_README.ko.md",
    "R039_MANIFEST.json",
    "R038_README.ko.md",
    "R038_MANIFEST.json",
    "R037_README.ko.md",
    "R037_MANIFEST.json",
    "R036_README.ko.md",
    "R036_MANIFEST.json",
    "R035_README.ko.md",
    "R035_MANIFEST.json",
    "R034_README.ko.md",
    "R034_MANIFEST.json"
  ],
  "unresolved": [],
  "complete": true
}
```
