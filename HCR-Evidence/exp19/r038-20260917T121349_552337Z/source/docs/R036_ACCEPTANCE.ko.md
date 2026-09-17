# R0.3.6 개발 검증 기록

## 실제 완료한 검증

작성/검증 환경: Linux, Python 3.13.5.

- 신규 도구 단위시험 96개: 통과 96, 실패 0, skip 0.
- 추가 전용 설치기 시험 17개: 통과 17, 실패 0, skip 0.
- 위 두 집합을 합친 최신 시험 수: 113개. 개발 중 같은 시험을 재실행한 횟수는 추가하지 않았다.
- 배포 Python 파일의 Python 3.12 문법 검사와 compile 검사.
- CLI/실행기 도움말, 필수 인자 누락, 별도 프로세스 단계 구성 검사.
- 배포 manifest와 ZIP 무결성·재추출 해시 검사.

단위시험은 8개 입력 변환에 대한 16개 Boolean world 대응 보존, 256개 관측 부호/결측 조합의 판별 가능성 검사, 관측된 gap 위치, 후보 제안과 완성 경로의 차이, 실제 R035 selector 및 독립 DAG 검사, 입력/부모/depth/값/summary/stream 변조, 비용 중복 집계 방지, 원자료 보존과 실패 시 중단을 포함한다.

## test double을 사용한 부분

native 재구성·native 실행·native auditor를 필요로 하는 단위시험에서는 해당 부분을 명시적인 test double로 교체했다. 실제 R035 `support_first`, 사후 지지 검사와 독립 proof auditor, 새 입력 변환/대응 검산, 진단·집계·파일 파이프라인은 실행했다. test double이 만든 session을 실제 native 실행으로 세지 않았다.

synthetic 상태, 단위시험 조합, 가짜 실행의 pipeline 성공을 EXP-17 연구 결과나 기존 엔진 통합 성공으로 해석하지 않는다.

## 아직 실행하지 않은 검증

이 작성 환경에는 전체 native 저장소 실행본을 확보하지 못했다. GitHub의 현재 기준선과 핵심 API 코드는 열람했으나, 아래는 실제로 실행하지 않았다.

- 실제 native 통합시험 7개(`native_tests/`).
- 기존 저장소 전체 회귀시험 및 실제 EXP-15 전체 원자료 재검산.
- 실제 EXP-17 128개 native trial과 전량 native auditor 실행.
- Windows / Python 3.12 인터프리터에서의 실행.
- 사용자 저장소에 대한 실제 패치 적용, commit 또는 push.

위 native 통합시험은 소스에 포함했고 `Run-HCR-R036.py`가 본 실험 전에 실행한다. native 모듈이나 원 EXP-15 자료가 없으면 skip으로 통과시키지 않고 실패한다. 통과 후에도 본 실험의 raw/evidence와 독립 audit 결과를 확인해야 한다.

## 개발 단계의 의미

현재 산출물은 **독립 구성요소와 실험 파이프라인 단위시험을 통과하고 로컬 native 통합 검사를 수행할 수 있도록 구성한 추가 소스 패치**다. EXP-17의 실제 결과는 아직 없다. 128이라는 값은 동결 설계의 trial 수이지 완료한 실험 수가 아니다.
