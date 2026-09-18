"""EXP-09 question revisited with EXP-24 measurement controls. Fixed before execution."""
BASE_COMMIT = '6b8ff8ab4c4858a3ab8f1a24e82b9033372133fc'
R043_MANIFEST_BLOB = '4a7467164dd82518c9193490c81623d6102d815f'
PARENT_RAW_SHA256 = '72cce1ef020908c4d2d9b3c219c68b1343d89d8a01d178a029518dc427f8e5e8'
PARENT_RUN = 'HCR-Evidence/exp22/r041-20260917T224012_261821Z'
PRIOR_RAW_SHA256 = '9f0575b86b968de5d924fc5777a1b1fdaa8fb0c7d67b0360cdbc8af44e3446fe'
PRIOR_RUN = 'HCR-Evidence/exp24/r043-20260918T002524_574380Z'
ORDERS = ('SMD','SDM','MSD','MDS','DSM','DMS')
VARIANTS = ('identity','swap_SD')
SCOPE = 'route_only'
ARM = 'online_support'
SCHEDULER = 'input_order'
PLAN_SCHEMA = 'hcr-exp25-plan-v1'
RAW_SCHEMA = 'hcr-exp25-raw-trial-v1'
RAW_MANIFEST_SCHEMA = 'hcr-exp25-raw-manifest-v1'
ANALYSIS_MANIFEST_SCHEMA = 'hcr-exp25-analysis-manifest-v1'
from .storage import ContractError, digest, require
