"""R042에서 새로 동결하는 상수. 기존 native/selector/scheduler는 변경하지 않는다."""
BASE_COMMIT = '11f43790c0cb1b4732199ae4fb17c5bbbed4cd5b'
R041_MANIFEST_BLOB = '71ba1f9f154341c63bb8e466dcc2a95d357f63af'
PARENT_RAW_SHA256 = '72cce1ef020908c4d2d9b3c219c68b1343d89d8a01d178a029518dc427f8e5e8'
PARENT_RUN = 'HCR-Evidence/exp22/r041-20260917T224012_261821Z'
SCHEDULERS = ('edge_id_min', 'edge_id_max')
VARIANTS = ('identity', 'swap_SD')
ORDERS = ('SMD', 'SDM', 'MSD', 'MDS', 'DSM', 'DMS')
EDGE_IDS = tuple('e' + str(i) for i in range(7))
SCOPE = 'legacy'
ARM = 'online_support'
PLAN_SCHEMA = 'hcr-exp23-plan-v1'
RAW_SCHEMA = 'hcr-exp23-raw-trial-v1'
RAW_MANIFEST_SCHEMA = 'hcr-exp23-raw-manifest-v1'
ANALYSIS_MANIFEST_SCHEMA = 'hcr-exp23-analysis-manifest-v1'
from .storage import ContractError, digest, require
