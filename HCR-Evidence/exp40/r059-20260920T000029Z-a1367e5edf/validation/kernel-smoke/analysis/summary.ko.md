# EXP-40 / R059 국소 교란 복원

실행 목적: implementation_validation

| condition | arm | final distance | tail max | recovered | band preserved |
|---|---|---:|---:|---|---|
| goal_i05 | control | 0.0 | 0.0 | None | True |
| goal_i05 | 4_minus | 8.049116928532385e-15 | 6.106226635438361e-14 | True | True |
| goal_i05 | 4_plus | 7.521760991835436e-15 | 6.059042156891792e-14 | True | True |
| goal_i09 | control | 0.0 | 0.0 | None | True |
| goal_i09 | 4_minus | 4.440892098500626e-16 | 4.440892098500626e-16 | True | True |
| goal_i09 | 4_plus | 0.0 | 0.0 | True | True |

128 tick의 유한시간 좌표 교란 복원 검사다. 수학적 attractor 또는 근방 전체의 안정성을 증명하지 않는다.
