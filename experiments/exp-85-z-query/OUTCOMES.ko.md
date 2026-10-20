# 실행 전 결과별 판단

| 관측 | 얻는 정보 | 다음 판단 |
|---|---|---|
| joint모든층/160질의/320eligibility정확,compact는productoracle정확하나conditional손실관측,unary보존 | 이판별표에서Z조건부상관보존과주변집합손실이분리됨 | 이유한slice경로의적합성만인정;최소성·효율은보류 |
| role/pair/membership부터오류 | 원천/역할/멤버십경계 | 최초실패source/Program/drive보존후원인판별 |
| membership정확하나3leafAND오류 | 새native triple결합경계 | 표현보존결론보류,정답수리/retune없이보존 |
| W정확하나projection/query입력/feasible오류 | 변환/공개slot/후속판독경계 | 해당층예측실패로남기고후속원인검사 |
| compact가productoracle와다름 | 개입구현또는native오류 | full오답을순수정보손실로채택하지않음 |
| consumer가rawsource/hash조회나사후query별producer로성공 | 격리·봉인계약위반 | 의미보존관측으로채택하지않음 |
| exact불일치/SHA/trace/resource실패 | 기준·엔지니어링·증거부족 | 이론음성아님;부분자료/inflight미확인호출보존,동일native재실행없음 |

실행전symbolic기대는compact full136/160,eligibility296/320,extraZ24,unary32/32다. 이는native관측이아니다. 정답kind만맞아도eligibility나중간값이틀리면보존성공으로채택하지않는다.
