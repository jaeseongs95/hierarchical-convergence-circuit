"""검증된 R038/R037 계약을 그대로 사용한다. raw/native schema는 재명명하지 않는다."""
from r038_early_adoption.contracts import (ARMS, SCOPES, Budget, SELECTION_LIMITS,
    USAGE_KEYS, digest, require, demand, finite_nonnegative, validate_public_observation)
BASE_COMMIT = '8713f17eedf684b8392f3d07d9d67a3b8f8f61cd'
R038_MANIFEST_BLOB = '6905f5c48cf257d1088f7bf605e18b2eb1421d58'
PARENT_RAW_SHA256 = '69d655930b59e66f23cc479ecc612a7bfbadd3038d894d51467b755323bf5a02'
CANONICAL_CASE = 'three_branch_l3_early'
CANONICAL_OBSERVATION_SHA256 = '9cebe2f351c4372d6e8bef7a952c79482776acf4f62e29aa7966a010510da1a6'
