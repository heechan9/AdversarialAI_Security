// Original teaching content: public PaulGuard aggregates and labeled synthetic cases.
export type Locale = "ko" | "en";
export type Text = { ko: string; en: string };
export const text = (ko: string, en: string): Text => ({ ko, en });
export type Choice = { id: string; label: Text; misconception?: string };
export type Concept = { id: string; title: Text; prerequisites: string[]; explanation: Text; evidence: string[] };
export type Question = { id: string; prompt: Text; choices: Choice[]; correct: string; concepts: string[] };
export const CONTENT_VERSION = "paulguard-evidence-learning-20261110-v1";
const repo = "https://github.com/heechan9/AdversarialAI_Security/blob/3ffc32b46002075f78cf7fb57a9b0d8b05b1d99d/";
export const sources = [
  { id: "public-matrix", title: text("공개 고정 배열 진단", "Public fixed-array diagnostic"), url: repo + "docs/STAGE_B_FIXED_ARRAY_20261110.md" },
  { id: "public-filter", title: text("공개 Gaussian 저장 결과", "Public saved Gaussian results"), url: repo + "results/defenses/experimental/gaussian_run_01/summary.json" },
  { id: "synthetic-prob", title: text("학습용 합성 확률 · 실제 추론 아님", "Synthetic probabilities · no actual inference"), url: null },
  { id: "synthetic-transfer", title: text("새 조건 합성 확인 · 새 실험 아님", "Synthetic transfer check · no new experiment"), url: null },
] as const;
export const concepts: Concept[] = [
  { id: "label", title: text("분류 라벨", "Class label"), prerequisites: [], evidence: ["synthetic-prob"], explanation: text("가장 큰 출력 성분으로 선택한 이름이 라벨입니다. 같은 이름을 골라도 전체 출력값은 다를 수 있습니다.", "The largest output component determines the label. Choosing the same name does not make every output value identical.") },
  { id: "probability", title: text("출력 확률과 정확도", "Output probability and accuracy"), prerequisites: ["label"], evidence: ["synthetic-prob", "public-matrix"], explanation: text("확률 벡터는 각 클래스의 출력값입니다. 정확도는 정답과 비교한 여러 표본의 비율이므로 한 출력 점수나 라벨 일치 횟수와 다릅니다.", "A probability vector contains output values for each class. Accuracy compares predictions with ground truth over a cohort; it is distinct from one score or a count of agreeing labels.") },
  { id: "epsilon", title: text("교란 크기 ε", "Perturbation budget ε"), prerequisites: [], evidence: ["public-filter"], explanation: text("정규화된 [0,1] 입력에서 L∞ ε=.01은 성분별 변화의 상한입니다. 공격 성공 확률이나 모든 이미지의 같은 변화량을 뜻하지 않습니다.", "For normalized [0,1] inputs, L-infinity ε=.01 bounds each component's change. It is not the chance of attack success or a requirement that every pixel changes equally.") },
  { id: "defense", title: text("공격 조건과 방어의 한계", "Attack conditions and defense limits"), prerequisites: ["epsilon"], evidence: ["public-filter", "synthetic-transfer"], explanation: text("같은 공격에 필터를 적용한 조건과 필터를 고려해 만든 공격은 다릅니다. 필터나 적대적 학습의 한 조건 개선은 모든 공격의 안전 보장이 아닙니다.", "Filtering an existing attack differs from generating an attack that accounts for the filter. Improvement under one filter or adversarial-training condition does not guarantee safety against every attack.") },
  { id: "fixed", title: text("입력 고정과 생성 단계", "Fixed scoring inputs and generation"), prerequisites: ["label"], evidence: ["public-matrix"], explanation: text("저장 배열을 고정해 분류하면 분류 환경의 차이를 살필 수 있습니다. 배열을 만드는 경사 계산·전처리·연산 문맥의 원인을 같은 실험으로 확정할 수는 없습니다.", "Scoring fixed saved arrays probes differences between scoring environments. It does not identify the causes of gradients, preprocessing or computation context during array generation.") },
  { id: "scope", title: text("표본과 검증 범위", "Samples and verification scope"), prerequisites: ["fixed"], evidence: ["public-matrix"], explanation: text("4/4는 교차표 완료 칸이고 10/10은 같은 배열의 라벨 비교 쌍입니다. 선택 4장·5조건을 반복한 것으로 전체 정확도·독립 재현·Stage B PASS의 분모가 아닙니다.", "4/4 counts completed matrix cells; 10/10 counts same-array label pairs. Four selected images and five conditions are reused, so these are not denominators for full accuracy, independent reproduction or Stage B PASS.") },
];
export const diagnosis: Question[] = [
  { id: "d-prob", prompt: text("출력이 [0.60, 0.40]과 [0.61, 0.39]라면 무엇이 같나요?", "With outputs [0.60, 0.40] and [0.61, 0.39], what agrees?"), correct: "label-only", concepts: ["label", "probability"], choices: [
    { id: "label-only", label: text("선택 라벨만 같고 벡터는 다름", "The selected labels agree; the vectors differ") },
    { id: "all-same", label: text("라벨이 같으므로 모든 확률도 같음", "Matching labels mean all probabilities match"), misconception: "label-is-vector" },
    { id: "accuracy", label: text("두 모델의 전체 정확도가 100%", "Both models have 100% full accuracy"), misconception: "agreement-is-accuracy" },
  ] },
  { id: "d-budget", prompt: text("[0,1] 입력의 L∞ ε=.01은 무엇인가요?", "What does L-infinity ε=.01 mean for [0,1] inputs?"), correct: "bound", concepts: ["epsilon", "defense"], choices: [
    { id: "chance", label: text("공격 성공 확률 1%", "A 1% chance of attack success"), misconception: "epsilon-is-success" },
    { id: "bound", label: text("성분별 입력 변화의 상한", "An upper bound on each input component's change") },
    { id: "safe", label: text("필터 적용 시 모든 공격에 안전", "Safety against every attack after filtering"), misconception: "defense-guarantee" },
  ] },
  { id: "d-scope", prompt: text("같은 저장 배열의 Windows/Linux 라벨 일치는 무엇을 말하나요?", "What does Windows/Linux label agreement on the same saved arrays establish?"), correct: "selected-scoring", concepts: ["fixed", "scope"], choices: [
    { id: "cause", label: text("공격 생성 차이의 단일 원인까지 해결", "The single cause of generation differences is resolved"), misconception: "scoring-is-generation" },
    { id: "pass", label: text("전체 Stage B 독립 재현 PASS", "Full independent Stage B reproduction passed"), misconception: "selected-is-full" },
    { id: "selected-scoring", label: text("해당 선택 입력의 분류 라벨 비교", "A scoring-label comparison for the selected inputs") },
  ] },
];
export type Scenario = { id: string; title: Text; kind: Text; setup: Text; question: Text; predictions: Choice[]; predictionCorrect: string; reasons: Choice[]; reasonCorrect: string; hints: Text[]; explanation: Text; check: Question & { explanation: Text }; concepts: string[]; evidence: string[] };
export const scenarios: Scenario[] = [
  { id: "probabilities", title: text("이름이 같으면 숫자도 같을까?", "Same name, same numbers?"), kind: text("합성 시나리오", "Synthetic scenario"), setup: text("두 클래스 A/B의 저장 출력 예시가 [0.55, 0.45], [0.550002, 0.449998]입니다. 실제 모델 추론 결과가 아닌 학습용 수치입니다.", "Two stored-output examples for classes A/B are [0.55, 0.45] and [0.550002, 0.449998]. These are teaching numbers, not actual model outputs."), question: text("어떤 비교 결과가 예상되나요?", "What comparison result do you expect?"), predictions: [
    { id: "label-same", label: text("라벨은 A로 같지만 확률은 다름", "Both labels are A, but probabilities differ") },
    { id: "vector-same", label: text("라벨과 확률 벡터가 모두 같음", "Both labels and probability vectors match"), misconception: "label-is-vector" },
    { id: "truth", label: text("두 예측 모두 실제 정답임", "Both predictions are correct against ground truth"), misconception: "agreement-is-accuracy" },
  ], predictionCorrect: "label-same", reasons: [
    { id: "argmax", label: text("최대 성분 위치는 같지만 성분 값은 다름", "The largest component has the same position, while values differ") },
    { id: "confidence", label: text("점수가 높으면 실제 정답임", "A high score guarantees a correct answer"), misconception: "score-is-truth" },
    { id: "rounding", label: text("반올림 표시가 같으면 원본 값도 같음", "Equal rounded display values mean exact original equality"), misconception: "rounding-is-exact" },
  ], reasonCorrect: "argmax", hints: [text("이름을 고르는 규칙과 숫자 전체를 비교하는 규칙을 나눠 보세요.", "Separate the rule for choosing a name from comparing every number."), text("각 벡터에서 가장 큰 성분의 위치를 먼저 찾고, 그다음 성분 값을 비교하세요.", "Find the largest component's position in each vector, then compare the component values.")], explanation: text("두 벡터 모두 A 성분이 가장 커 라벨은 같습니다. 성분 값은 달라 확률 벡터는 일치하지 않습니다. 정답 정보와 표본 집합이 없으므로 전체 정확도를 구할 수 없습니다.", "A is the largest component in both vectors, so labels agree. Component values differ, so vectors do not match. Without ground truth and a cohort, full accuracy cannot be calculated."), concepts: ["label", "probability"], evidence: ["synthetic-prob"], check: { id: "c-prob", prompt: text("새 합성 조건: [0.49,0.51]과 [0.52,0.48]이면?", "New synthetic condition: what about [0.49,0.51] and [0.52,0.48]?"), correct: "different", concepts: ["probability"], choices: [
    { id: "same", label: text("확률 차이가 작으니 라벨은 같음", "The probability difference is small, so labels agree"), misconception: "small-is-same" },
    { id: "different", label: text("최대 성분 위치가 달라 라벨도 다름", "The largest-component positions differ, so labels differ") },
  ], explanation: text("첫 벡터는 B, 둘째는 A를 선택합니다. 작은 확률 차이도 순위를 바꿀 수 있습니다.", "The first vector selects B and the second selects A. A small probability difference can change the ordering.") } },
  { id: "defense-conditions", title: text("필터를 적용한 공격과 필터를 아는 공격", "Filtering an attack versus an attack that knows the filter"), kind: text("공개 저장 결과 시나리오", "Public saved-result scenario"), setup: text("MobileNetV2·Gaussian·ε=.01, 시험 파일 781장입니다. 기존 공격에 필터를 적용한 보고서와 필터를 고려해 생성한 공격 보고서를 따로 엽니다. 새 실행은 하지 않습니다.", "MobileNetV2, Gaussian, ε=.01, with 781 test files. Reports for filtering an existing attack and an attack generated with filter awareness are opened separately. No new execution occurs."), question: text("보고서를 열기 전에 어떤 해석을 예상하나요?", "Before opening the reports, which interpretation do you expect?"), predictions: [
    { id: "safe", label: text("필터 하나로 모든 공격에서 안전", "One filter ensures safety against all attacks"), misconception: "defense-guarantee" },
    { id: "distinct", label: text("두 공격 조건의 결과는 다를 수 있음", "Results can differ between the two attack conditions") },
    { id: "percent", label: text("ε=.01이므로 공격 성공률은 1%", "With ε=.01, attack success must be 1%"), misconception: "epsilon-is-success" },
  ], predictionCorrect: "distinct", reasons: [
    { id: "aware", label: text("두 번째 공격은 필터를 포함한 경로를 고려함", "The second attack accounts for the path that includes the filter") },
    { id: "same", label: text("같은 이미지 수면 모든 조건이 같음", "The same image count makes all conditions identical"), misconception: "same-n-same-condition" },
    { id: "training", label: text("필터는 자동으로 모델을 재학습함", "A filter automatically retrains the model"), misconception: "filter-is-training" },
  ], reasonCorrect: "aware", hints: [text("필터를 끼운 시점과 공격자가 알고 있는 범위를 비교해 보세요.", "Compare when the filter is applied and what the attacker accounts for."), text("기존 공격을 재사용했는지, 필터를 고려한 별도 공격인지가 다릅니다.", "Reusing an existing attack differs from a separate attack that accounts for the filter.")], explanation: text("보존된 정답 수는 정상613/781, 공격97/781, 전달 공격+필터341/781, 방어 인지 공격+필터74/781입니다. 방어 인지 ASR은 필터 정상 정답648장 중574장 오답 전환입니다. 781과648은 서로 다른 분모입니다. 조건별 결과이며 일반적 안전 보장이 아닙니다.", "Preserved correct counts are clean 613/781, attacked 97/781, transfer attack plus filter 341/781, and adaptive attack plus filter 74/781. Adaptive ASR is 574 failures among 648 correctly classified filtered clean inputs. 781 and 648 are different denominators. These are condition-specific results, not general safety guarantees."), concepts: ["epsilon", "defense"], evidence: ["public-filter"], check: { id: "c-defense", prompt: text("새 합성 조건: 적대적 학습 뒤 PGD7 정답이12/100→18/100으로 늘었다면? (실제 PaulGuard 결과 아님)", "New synthetic condition: after adversarial training, PGD7 correct counts rise 12/100 → 18/100. (Not a PaulGuard result.)"), correct: "limited", concepts: ["defense"], choices: [
    { id: "all-safe", label: text("모든 공격·강도에서 안전해졌음", "It is now safe against every attack and strength"), misconception: "training-guarantee" },
    { id: "limited", label: text("해당 조건에서의 변화만 관측함", "Only a change under the stated condition was observed") },
  ], explanation: text("다른 공격·강도·재시작·환경의 결과는 이 수치만으로 알 수 없습니다. 필터와 적대적 학습 모두 같은 일반화 경계를 지킵니다.", "This number does not determine results under other attacks, strengths, restarts or environments. The same generalization boundary applies to filters and adversarial training.") } },
  { id: "fixed-matrix", title: text("같은 배열의 분류와 배열 생성은 다른 질문", "Scoring the same arrays and generating arrays ask different questions"), kind: text("공개 선택 진단 시나리오", "Public selected-diagnostic scenario"), setup: text("선택4장·5조건의 저장 공격 배열 두 출처를 Windows와 Linux에서 각각 분류합니다. 교차표는2×2칸입니다. 결과를 해석할 범위를 먼저 예상하세요.", "Saved attack arrays from two origins, using four selected images and five conditions, are scored on Windows and Linux. The matrix has 2×2 cells. Predict the scope before opening the results."), question: text("분류 라벨이 모두 일치하더라도 무엇이 남을 수 있나요?", "Even if every scoring label agrees, what can remain unresolved?"), predictions: [
    { id: "remaining", label: text("공격 배열 생성 차이의 원인은 남을 수 있음", "The cause of attack-array generation differences can remain unresolved") },
    { id: "accuracy", label: text("전체781장 정확도가100%로 확정됨", "Full 781-image accuracy is established as 100%"), misconception: "agreement-is-accuracy" },
    { id: "external", label: text("외부 Stage B가 자동으로 PASS", "External Stage B automatically passes"), misconception: "selected-is-full" },
  ], predictionCorrect: "remaining", reasons: [
    { id: "separation", label: text("고정 입력의 분류만 비교하며 생성 단계와 전체 분모는 별도", "Only fixed-input scoring is compared; generation and the full cohort are separate") },
    { id: "os", label: text("같은 라벨이면 모든 OS 연산이 완전히 같음", "Equal labels prove every OS computation is identical"), misconception: "label-is-vector" },
    { id: "twenty", label: text("출력20개는 독립 이미지20장", "Twenty outputs mean twenty independent images"), misconception: "repeated-is-independent" },
  ], reasonCorrect: "separation", hints: [text("교차표의 칸, 라벨 쌍, 원래 이미지 수를 각각 세어 보세요.", "Count matrix cells, label pairs and original images separately."), text("공격 배열을 만드는 과정은 고정해 둔 배열을 분류하는 과정과 구분됩니다.", "Creating attack arrays is separate from scoring arrays that have already been fixed.")], explanation: text("공개 결과는4/4칸 완료, 같은 배열의 라벨10/10쌍 일치입니다. 확률 벡터는 완전히 같은 쌍이 없고 최대 성분 차이는2.9206275939941406e-6입니다. 출력20개는 이미지4장의 조건별 재사용입니다. 외부 Stage B FAIL, 생성 원인 UNRESOLVED는 유지합니다.", "The public result has 4/4 completed cells and 10/10 matching same-array label pairs. No probability-vector pair is exactly identical; the largest component difference is 2.9206275939941406e-6. Twenty outputs reuse four images across conditions. External Stage B remains FAIL and the generation cause remains UNRESOLVED."), concepts: ["fixed", "scope"], evidence: ["public-matrix"], check: { id: "c-scope", prompt: text("새 합성 조건: 선택3장의 같은 배열 라벨6/6쌍과 확률까지 같다면 전체 독립 재현을 승인할 수 있나요?", "New synthetic condition: on three selected images, all 6/6 same-array labels and probability vectors match. Does that approve full independent reproduction?"), correct: "no", concepts: ["scope"], choices: [
    { id: "yes", label: text("가능: 일치했으니 전체도 통과", "Yes: agreement means the full study passes"), misconception: "selected-is-full" },
    { id: "no", label: text("불가: 선택 범위의 일치와 전체 재현은 별도", "No: selected-scope agreement and full reproduction are separate") },
  ], explanation: text("확률까지 일치해도 표본과 조건의 범위는 넓어지지 않습니다. 전체 조건·독립 수행·원래 판정 근거를 별도로 확인해야 합니다.", "Even exact probabilities do not expand the sample or condition scope. Full conditions, independent execution and the original decision evidence require separate verification.") } },
];
export const publicFacts = {
  selectedImages: 4, conditionsPerCell: 5, completeCells: 4, totalCells: 4, matchingLabelPairs: 10, totalLabelPairs: 10,
  exactProbabilityPairs: 0, maxProbabilityDelta: 2.9206275939941406e-6, externalStageB: "FAIL", cause: "UNRESOLVED",
  gaussian: { epsilon: .01, correct: [613, 97, 341, 74], denominator: 781, adaptiveSuccess: 574, adaptiveDenominator: 648 },
} as const;
