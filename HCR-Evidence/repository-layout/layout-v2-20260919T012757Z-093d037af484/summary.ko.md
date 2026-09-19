# 저장소 구조 정리 결과

상태: **APPLIED_AND_VERIFIED**

이 기록은 구조 migration의 결과이며 HCC 연구 실험이나 가설 검증 결과가 아니다.

```json
{
  "moved_distribution_files": 19,
  "retained_referenced_distribution_files": 0,
  "created_navigation_files": 13,
  "original_files_in_snapshot": 12927,
  "existing_files_rewritten": 0,
  "audit": {
    "bytes_read_for_original_verification": 1126907304,
    "experiments_indexed": 31,
    "failures": [],
    "generated_files_checked": 13,
    "moves_checked": 19,
    "original_evidence_files_checked": 12056,
    "original_files_checked": 12927,
    "passed": true,
    "schema": "hcc-layout-independent-audit-v2",
    "scope": "local byte/path/index integrity; NOT an HCC experiment or external attestation"
  },
  "final_regression": [
    {
      "argv": [
        "C:\\Users\\sjs95\\AppData\\Local\\Programs\\Python\\Python312\\python.exe",
        "-X",
        "utf8",
        "-B",
        "D:\\codex\\진짜미친짓\\hierarchical-convergence-circuit\\HCC_REORGANIZE_V2\\regression_probe.py",
        "--root",
        "D:\\codex\\진짜미친짓\\hierarchical-convergence-circuit",
        "--suite",
        "core"
      ],
      "exit_code": 0,
      "seconds": 122.53100000000268,
      "log": "final-core.txt",
      "log_sha256": "e04da0eb2054b021eff85cb6365e87912903ec9858cb13af48ed4c1d0b637e20",
      "stats": {
        "errors": 0,
        "failures": 0,
        "skip_details": [
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
        "skipped": 3,
        "tests_run": 602
      },
      "acceptance": {
        "observed_skips": {
          "test_r021_sessions.CheckpointIO.test_file_symlink_rejected": "symlink creation is not available",
          "test_r021_sessions.CheckpointIO.test_symlink_parent_rejected": "symlink creation is not available",
          "test_r034_selection.ProtocolAndIO.test_symlink_rejected": "local symlink creation not supported"
        },
        "allowed_platform_skips": {
          "test_r021_sessions.CheckpointIO.test_file_symlink_rejected": "symlink creation is not available",
          "test_r021_sessions.CheckpointIO.test_symlink_parent_rejected": "symlink creation is not available",
          "test_r034_selection.ProtocolAndIO.test_symlink_rejected": "local symlink creation not supported"
        },
        "coverage_note": "Only the pinned, platform-conditional symlink skips may remain; fewer skips are accepted."
      }
    },
    {
      "argv": [
        "C:\\Users\\sjs95\\AppData\\Local\\Programs\\Python\\Python312\\python.exe",
        "-X",
        "utf8",
        "-B",
        "D:\\codex\\진짜미친짓\\hierarchical-convergence-circuit\\HCC_REORGANIZE_V2\\regression_probe.py",
        "--root",
        "D:\\codex\\진짜미친짓\\hierarchical-convergence-circuit",
        "--suite",
        "r047_state_ablation"
      ],
      "exit_code": 0,
      "seconds": 4.014999999999418,
      "log": "final-r047_state_ablation.txt",
      "log_sha256": "08ee354fce0588ad4d7018f57cfae0bce8ee052b417452d263086a2d8893e478",
      "stats": {
        "errors": 0,
        "failures": 0,
        "skip_details": [],
        "skipped": 0,
        "tests_run": 65
      },
      "acceptance": {
        "observed_skips": {},
        "allowed_platform_skips": {},
        "coverage_note": "Only the pinned, platform-conditional symlink skips may remain; fewer skips are accepted."
      }
    },
    {
      "argv": [
        "C:\\Users\\sjs95\\AppData\\Local\\Programs\\Python\\Python312\\python.exe",
        "-X",
        "utf8",
        "-B",
        "D:\\codex\\진짜미친짓\\hierarchical-convergence-circuit\\HCC_REORGANIZE_V2\\regression_probe.py",
        "--root",
        "D:\\codex\\진짜미친짓\\hierarchical-convergence-circuit",
        "--suite",
        "r048_precision"
      ],
      "exit_code": 0,
      "seconds": 6.672000000005937,
      "log": "final-r048_precision.txt",
      "log_sha256": "527c82d89e2a1179c18399b3ece605d777fec3c8a18cdaafedf978fc7a381dc4",
      "stats": {
        "errors": 0,
        "failures": 0,
        "skip_details": [],
        "skipped": 0,
        "tests_run": 40
      },
      "acceptance": {
        "observed_skips": {},
        "allowed_platform_skips": {},
        "coverage_note": "Only the pinned, platform-conditional symlink skips may remain; fewer skips are accepted."
      }
    },
    {
      "argv": [
        "C:\\Users\\sjs95\\AppData\\Local\\Programs\\Python\\Python312\\python.exe",
        "-X",
        "utf8",
        "-B",
        "D:\\codex\\진짜미친짓\\hierarchical-convergence-circuit\\HCC_REORGANIZE_V2\\regression_probe.py",
        "--root",
        "D:\\codex\\진짜미친짓\\hierarchical-convergence-circuit",
        "--suite",
        "r049_signal_boundary"
      ],
      "exit_code": 0,
      "seconds": 5.140999999988708,
      "log": "final-r049_signal_boundary.txt",
      "log_sha256": "f1324e3fb3ea84d18cb75f8be7a148034548334ad102a919c593641e7e6499dc",
      "stats": {
        "errors": 0,
        "failures": 0,
        "skip_details": [],
        "skipped": 0,
        "tests_run": 95
      },
      "acceptance": {
        "observed_skips": {},
        "allowed_platform_skips": {},
        "coverage_note": "Only the pinned, platform-conditional symlink skips may remain; fewer skips are accepted."
      }
    }
  ],
  "regression_stage_count": 1,
  "preorganization_project_regression_runs": 0,
  "git_index_and_head_unchanged": true,
  "research_runs_executed": 0,
  "note": "Preflight used metadata/path/hash checks only. Full project regression ran once after organization."
}
```
