"""Cap canonical payload bytes in addition to record/count/raw bounds."""
from tools.r36_overlap_composition.recording import Recorder as PriorRecorder,work_writer
from tools.r32_semantic_join.runtime import require

class Recorder(PriorRecorder):
    def add(self,k):
        key=super().add(k)
        require(self.cached_bytes<=self.p['budget']['canonical_cache_bytes'],'canonical cache byte stop boundary')
        return key
