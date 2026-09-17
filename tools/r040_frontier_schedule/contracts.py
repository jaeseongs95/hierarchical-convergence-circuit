"""기존 계산/선택 예산은 유지하고 scheduling 개입만 추가한다."""
from r038_early_adoption.contracts import (ARMS, SCOPES, BASE_POLICY, Budget,
    SELECTION_LIMITS, USAGE_KEYS, digest, require, demand, finite_nonnegative,
    validate_public_observation)
BASE_COMMIT = 'ef074f7991733ba0a73d870780d4873718caf1ca'
R039_MANIFEST_BLOB = 'daca0bdbbe8bdf3e45e2e7f0a632b84e4a1ae8ca'
PARENT_RAW_SHA256 = '3dd7fcef33f6f9b00af158892d35294ad34311bb4ea9ff7db7d31567cbe05e26'
SCHEDULERS = ('input_order','edge_id_min')
SCHEDULE_USAGE = ('decision_calls','frontier_items_examined','edge_id_reads',
                  'key_comparisons','priority_transitions','priority_match_scans')
