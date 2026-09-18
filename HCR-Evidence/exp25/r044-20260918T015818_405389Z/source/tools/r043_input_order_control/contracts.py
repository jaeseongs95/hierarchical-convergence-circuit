"""Pinned EXP23 results -> EXP24 input-order negative control."""
BASE_COMMIT = 'eedb04f90f02cf3c55693d493d33db18f96a23b5'
R042_MANIFEST_BLOB = '3e1447a50b2e0938a10468ce428b6b76a8d28d86'
PARENT_RAW_SHA256 = '72cce1ef020908c4d2d9b3c219c68b1343d89d8a01d178a029518dc427f8e5e8'
PARENT_RUN = 'HCR-Evidence/exp22/r041-20260917T224012_261821Z'
PRIOR_RAW_SHA256 = '2416de7b40542568db2055335b3be23d15bc98505219b3eccfc3f666f4544645'
PRIOR_RUN = 'HCR-Evidence/exp23/r042-20260917T233524_872976Z'
SCHEDULERS = ('input_order',)
VARIANTS = ('identity', 'swap_SD')
ORDERS = ('SMD', 'SDM', 'MSD', 'MDS', 'DSM', 'DMS')
EDGE_IDS = tuple('e' + str(i) for i in range(7))
SCOPE = 'legacy'
ARM = 'online_support'
PLAN_SCHEMA = 'hcr-exp24-plan-v1'
RAW_SCHEMA = 'hcr-exp24-raw-trial-v1'
RAW_MANIFEST_SCHEMA = 'hcr-exp24-raw-manifest-v1'
ANALYSIS_MANIFEST_SCHEMA = 'hcr-exp24-analysis-manifest-v1'
from .storage import ContractError, digest, require
