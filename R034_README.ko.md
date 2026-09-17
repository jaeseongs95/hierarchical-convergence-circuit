# HCR R0.3.4 — EXP-15 추가 패치

EXP-14 결과를 바탕으로 **추가 전개 / 같은 정책 재시작 / judgment prior 변경 / 생성된 proof 선택**을 비교한다.

기준 commit: `54330d01c979cb942b39558186c206b4373b758e`.
기존 엔진·학습·pool·원래 proof 생성·EXP-14·기존 README는 수정하지 않는다. 새 기능은 별도 모듈과 `Run-HCR-R034.py`로 실행한다.

- [설계와 연구 경계](docs/R034_DESIGN.ko.md)
- [적용·실행과 결과 경로](docs/R034_USAGE.ko.md)
- [작성 환경의 실제 검증 범위](docs/R034_ACCEPTANCE.ko.md)
- [EXP-15 동결 설계](experiments/exp-15-proof-selection/design.md)

```powershell
python -X utf8 -B Run-HCR-R034.py --out HCR-Evidence/exp15/r034-first
```

원 native decision과 새 sidecar proof를 구별한다. 기존 경로만 검사하며 새 관측 없이 없는 정보를 만들어내지 않는다. main 182개와 별도 대조군 12개, 총 194 rollout을 계획한다. 독립 검산 후 요약은 `HCR-Evidence/exp15/r034-first/analysis/summary.ko.md`다.

추가 파일의 무결성은 `R034_MANIFEST.json`으로 검사한다. 과거 release manifest와 버전 문자열을 소급 변경하지 않는다.
