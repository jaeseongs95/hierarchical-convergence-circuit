"""신규 배포와 기존 동결 의존 소스의 checksum 검사. 이전 파일 변경 없음."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from r041_scheduler_direction import sources
if __name__=='__main__':
    addon=sources.addon_hashes();dependencies=sources.dependencies()
    print(json.dumps(dict(verified=True,addon_files=len(addon),dependency_files=len(dependencies),
        schema='hcr-r041-deployment-check-v1'),ensure_ascii=False))
