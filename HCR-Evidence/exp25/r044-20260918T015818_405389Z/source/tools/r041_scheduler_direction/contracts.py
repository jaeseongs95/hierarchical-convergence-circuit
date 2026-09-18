"""기존 계산/선택 예산은 유지하고 scheduling 개입만 추가한다."""
from r038_early_adoption.contracts import (ARMS, SCOPES, BASE_POLICY, Budget,
    SELECTION_LIMITS, USAGE_KEYS, digest, require, demand, finite_nonnegative,
    validate_public_observation)
BASE_COMMIT = '37bb3c19f27dfbd73de7519fc8cad399395bcf3a'
R040_MANIFEST_BLOB = 'd7213c8c9415016a047ed0004ff3ffd7ac43366a'
PARENT_RAW_SHA256 = '18075ae1ad5fe4eba29161948bbb89218a5eed02bd688972962728e0a55f7464'
SCHEDULERS = ('input_order','edge_id_min','edge_id_max')
BASELINE_SCHEDULERS = ('input_order','edge_id_min')
SCHEDULE_USAGE = ('decision_calls','frontier_items_examined','edge_id_reads',
                  'key_comparisons','priority_transitions','priority_match_scans')
