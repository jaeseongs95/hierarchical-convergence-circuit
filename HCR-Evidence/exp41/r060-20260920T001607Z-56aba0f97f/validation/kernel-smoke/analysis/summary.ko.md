# EXP-41 / R060 동시 좌표 교란 복원

실행 목적: implementation_validation

| condition | arm | final distance | tail max | recovered | band preserved |
|---|---|---:|---:|---|---|
| goal_i05 | control | 0.0 | 0.0 | None | True |
| goal_i05 | mmmmm | 3.3353042550032796e-12 | 2.6031510280688508e-11 | True | True |
| goal_i05 | mpmpm | 2.7589597273447453e-12 | 2.1532498006848755e-11 | True | True |
| goal_i05 | ppppp | 3.3384683906234613e-12 | 2.605968218993837e-11 | True | True |
| goal_i09 | control | 0.0 | 0.0 | None | True |
| goal_i09 | mmmmm | 4.440892098500626e-16 | 4.440892098500626e-16 | True | True |
| goal_i09 | mpmpm | 4.440892098500626e-16 | 4.440892098500626e-16 | True | True |
| goal_i09 | ppppp | 0.0 | 0.0 | True | True |

128 tick의 유한시간 동시 좌표 교란 복원 검사다. 수학적 attractor 또는 근방 전체의 안정성을 증명하지 않는다.
