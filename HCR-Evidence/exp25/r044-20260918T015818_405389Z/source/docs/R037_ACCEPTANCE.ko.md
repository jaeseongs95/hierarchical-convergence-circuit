# R037 배포 검토 및 실제 검증 범위

기준 커밋: `b6b57589e18cc4be97cea10515f90ffbf100218f`.
배포 형태: 신규 파일만 추가하는 overlay. 기존 native/R035/R036 소스와 원자료 수정 없음. 원격 Git 작업 없음.

## 수행한 검사

| 검사 | 결과 | 증거 |
|---|---|---|
| 신규 단위 테스트 | 93개 통과 | `validation/r037/unit_tests.txt` |
| 고정 seed synthetic 경계 조합 | 200개 검사 통과. 위 단위 테스트 수에 포함 | `test_boundary_fuzz.py`, unit 로그 |
| 실제 R035 selector 연결 테스트 | 16개 통과. Graph 상태는 synthetic | `validation/r037/selector_tests.txt` |
| Python 3.12 문법 검사 | 25개 Python 파일 통과 | `validation/r037/syntax.txt` |
| 현재 환경의 Python compile | 25개 파일 통과 | 같은 로그 |
| selector 기준 소스 identity | 원격 Git blob SHA 2개 일치 | `validation/r037/environment_and_scope.json` |

실행 환경은 Linux의 Python **3.13.5**다. Python 3.12 호환 문법을 별도로 파싱했지만 Windows/Python 3.12에서 실제 실행한 결과로 표기하지 않는다.

실제 호출한 baseline selector 파일의 Git blob SHA는 다음과 같다.

```text
R035 contracts.py  b22321250f729450cc04917321a49fbae5df4970
R035 selection.py  e5b83efa7126cfdfff22cedbdef8635fbd294b7a
```

원격에서 읽은 파일을 별도 검사용 위치에 복원하고 byte-level Git blob hash를 확인했다. 이 두 기존 파일은 신규 ZIP에 포함하거나 덮어쓰지 않는다. 연결 검사에서는 실제 기존 `run_policy`와 신규 `NativeBackend.select`를 호출했고, 일부 검사는 synthetic session의 온라인 종료까지 연결했다. **Native Graph 생성 또는 실제 모델 실험을 검증한 것은 아니다.**

## 테스트에서 확인한 계약

처음 나온 native candidate를 선택기 호출 전에 보존하고, selector 오류·입력 변경·허위 raw 반전·비용 변조를 거부한다. 초기 예산 소진 시 가짜 readout을 만들지 않고, 추가 계산 미완성과 마지막 readout을 구분한다. 예산 밖의 추가 계산, 종료 이후 숨은 작업, 누락된 readout, policy identity 변경, 미등록 event를 독립 제어 검산에서 검출한다.

원자료·계획의 덮어쓰기, parent/source 변경, 경로 탈출, symlink, 중복 JSON key, 비유한 JSON 값, production 실행의 synthetic backend 혼입을 검사했다. runtime 실패 시 부분 원문과 failure 상태를 보존하며 자동 retry가 없음을 확인했다. JSON으로 직렬화할 수 없는 부분 상태도 repr 원문과 별도 오류로 남기도록 검사했다.

보고서 테스트에서는 보류/미관측/오답의 차이, 첫·마지막·terminal 시점의 비중복 집계, paired 비교, 누적 비용 합산을 검사했다. 관측 지지를 받는 출력이 외부 대조 라벨과 다를 수 있는 synthetic 사례를 포함했다.

실제 selector 연결 검사에서는 지지 경로가 미완성인 경우의 보류, 완성된 낮은 activation 경로 채택, native 원 proof 유지, activation 부적격, 0/음수 관측, raw 값 보존, ranking/scan/proof 예산 종료, 비공개 필드 거부, selector 비용 분리, 채택 뒤 실제 추가 작업 중단을 확인했다.

## 수행하지 않은 검사

저장소 전체와 원 native 환경을 로컬에 확보하지 못했으므로 다음은 **미실행**이다.

- 기존 native 전체 회귀 및 EXP-17 전체 독립 재검증.
- 신규 `native_tests/`의 7개 실제 native 통합 검사.
- 본 EXP-18의 32개 fresh native trial 및 그 결과의 독립 audit/verify.

Native 통합 검사는 2개 진단 입력 × 2개 prior × 2개 selector의 실제 session 8개를 공유한다. 원 native 출력의 EXP-17 parity, 첫 view 일치, 원자료 독립 재생, raw 값 비반전, frozen memory, 변조 거부를 검사한다. 정확도 개선을 합격 조건으로 강제하지 않는다.

`Run-HCR-R037.py`는 위 미실행 검사를 실제 저장소에서 필수 단계로 수행한다. import 실패나 원자료 누락을 skip이나 synthetic 결과로 바꾸지 않으며, 첫 실패에서 본 실험 전에 중단한다. 따라서 이 배포를 '전체 native 실행 검증 완료'라고 해석해서는 안 된다.

## 배포 무결성 및 사용 기준

`R037_MANIFEST.json`은 배포 파일의 SHA256을 담는다. 소스 텍스트의 LF/CRLF 차이는 정규화하되, 실험 원자료 checksum은 원 byte 기준으로 유지한다. `scripts/verify_r037.py --addon-only`는 신규 배포 파일만, 옵션 없는 명령은 고정된 기존 baseline까지 검사한다.

기존 source/원자료/실패 기록을 그대로 두고, 신규 파일을 저장소 루트에 병합한다. 실제 실험 결과가 올라온 뒤에는 예상된 개선 여부보다 raw packet·원 candidate·채택 proof·제어 action·독립 audit의 일치를 우선 검토한다.
