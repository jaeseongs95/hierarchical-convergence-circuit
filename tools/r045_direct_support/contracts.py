"""Frozen design identifiers. Research predictions are never acceptance criteria."""
BASE_COMMIT = '3bfeb64af877a7512071798fd77d8eba839760a1'
R044_MANIFEST_BLOB = '86eaf459d963220845512c766b707ba3b4c0a1f6'
PARENT_RUN = 'HCR-Evidence/exp25/r044-20260918T015818_405389Z'
PARENT_RAW_SHA256 = '24b88d417b107b0d6a92c1187c52b2ef0b14a313beab90e6025d23c872129bcf'
FAMILIES = ('supported_len2', 'no_match_len1', 'conflict_len2')
VARIANTS = ('identity', 'fresh_ids')
SCORE = 0.92
TRIAL_COUNT = 12
PLAN_SCHEMA = 'hcr-exp26-plan-v1'
RAW_SCHEMA = 'hcr-exp26-raw-trial-v1'
RAW_MANIFEST_SCHEMA = 'hcr-exp26-raw-manifest-v1'
ANALYSIS_MANIFEST_SCHEMA = 'hcr-exp26-analysis-manifest-v1'
from .storage import ContractError, digest, require
