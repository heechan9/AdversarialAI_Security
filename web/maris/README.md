# MARIS · 해양 AI 가상 실험실

선박 이미지 분류기의 Clean / FGSM 기록을 탐색하는 독립 시각화 앱입니다.
Three.js의 설명용 해상 장면, 기록된 비교 그림 4개, 두 모델의 전체·클래스별
결과를 연결합니다. 실시간 추론·항해 제어·방어 실험을 수행하지 않습니다.

## 연구 근거

원본 저장소: https://github.com/heechan9/AdversarialAI_Security

기준 커밋은 `public/evidence/provenance.json`에 고정되어 있습니다.
기존 연구 결과를 수정하지 않고 감사 통과한 표본 기록만 읽어 내보냅니다.

```bash
python scripts/export-evidence.py --repo /path/to/AdversarialAI_Security
node scripts/test-evidence.mjs
node scripts/test-interactions.mjs
pnpm dev
```

내보내기에는 원 저장소 감사기의 Python 의존성이 필요합니다. 모델·원본 이미지나
TensorFlow 추론은 필요하지 않습니다. `pnpm-lock.yaml`이 웹 의존성 기준입니다.
`VALIDATION.md`에 실제 검증 범위와 환경 한계를 기록합니다.

## 표시 계약

- 정확도 분모는 해당 전체 표본, ASR 분모는 clean-correct 표본.
- 분모 0인 클래스의 ASR은 null이며 정의 불가로 표시.
- 결과는 provisional이며 기록된 epsilon만 사용. 보간 금지.
- 이미지 파일은 원 저장소의 비교 그림을 바이트 그대로 복사; CSS로 각 패널 표시.
- 공격 입력의 출력 점수는 원 기록에 없어 표시하지 않음.
- 3D는 동일 선박·운항 상황을 재현하는 모델이 아닌 설명용 geometry.
- WebGL 사용 불가 시 같은 3D geometry와 camera를 SVGRenderer로 표시.

## 직접 조작과 비교

- 선박: 드래그 / 한 손가락 회전, 휠 / 두 손가락 핀치 확대. 이동(pan)은
  막고 거리와 수직 각도를 제한합니다. 조작 시작 시 자동 회전은 꺼집니다.
  시점 초기화는 남은 관성을 지운 뒤 저장한 카메라와 주시점을 복원합니다.
- 두 입력 그림: 공유 배율 1–3배, 공유 위치 이동, 탭 간 동일 위치 유지.
  이는 저장 PNG의 화면 확대이며 원본 배열에서 새 이미지를 계산하지 않습니다.
- 기존 차이 패널: RGB 채널별 절대 차이를 이미지 내 전체 최대 절대 차이로
  나눈 그림입니다. 원본 배열이나 그 최댓값이 없어 새로운 지도·수치 배율을
  만들지 않습니다. 흰색은 상대 차이가 큰 채널들을 나타내며 성공/주목도가 아닙니다.
- 강도별 막대그래프: 검증된 결과 객체에서 정확도와 ASR을 계산합니다.
  전체 통계 선택과 개별 사례를 별도 표시하며 명시적 맞추기 버튼만 연동합니다.
- 시각 사례는 항공모함의 성공 2개 / 실패 2개로 제한됩니다. 다른 선종을
  추가하려면 표본 경로·모델·epsilon으로 연결되는 감사 가능한 산출물이 필요합니다.

구현·증거 연결·검증: Codex. 원본 연구의 기여는 원 저장소 CONTRIBUTIONS.md를
따르며 이 앱의 구현이 팀원의 독립 실험 검증을 대체하지 않습니다.
