"use client";
import { useLocale } from "./locale-provider";
import snapshot from "../public/evidence/fixed-array-cross-score.json";

const details = "https://github.com/heechan9/AdversarialAI_Security/blob/main/docs/STAGE_B_FIXED_ARRAY_20261110.md";

export default function FixedArrayCrossScore() {
    const { locale } = useLocale();
    const en = locale === "en";
    const same = snapshot.same_array_cross_environment;
    const completed = (origin: string, scorer: string) => snapshot.cells.find(cell => cell.attack_origin === origin && cell.scorer === scorer)?.selected_outputs;
    return <section id="cross-score" className="results-section research-diagnostics" aria-labelledby="cross-score-title">
        <div className="section-heading"><div><span className="eyebrow">FIXED INPUTS · 2026-11-10</span>
            <h2 id="cross-score-title">{en ? "Same saved inputs, two scoring environments." : "같은 저장 입력을 두 환경에서 분류했어요."}</h2>
        </div></div>
        <div className="diagnostic-panel">
            <p className="diagnostic-intro">{en
                ? "A selected MobileNetV2 diagnostic: PC- and Linux-generated attack arrays were each scored on Windows and Linux. Four images and five selected conditions per cell; these counts are not accuracy measurements."
                : "MobileNetV2 선택 진단입니다. PC와 Linux에서 생성했던 공격 배열을 각각 Windows와 Linux에서 분류했습니다. 칸마다 선택 이미지 4장·조건 5개이며, 아래 개수는 정확도가 아닙니다."}</p>
            <div className="diagnostic-metrics">
                <div><span>{en ? "Completed matrix cells" : "완료한 교차표 칸"}</span><strong>{snapshot.completed_cells} / {snapshot.total_cells}</strong></div>
                <div><span>{en ? "Same-array matching label pairs" : "같은 배열의 환경 간 라벨 일치"}</span><strong>{same.matching_label_pairs} / {same.compared_label_pairs}</strong></div>
                <div><span>{en ? "Largest probability component difference" : "최대 확률 성분 차이"}</span><strong>2.92 × 10⁻⁶</strong></div>
            </div>
            <div className="diagnostic-table"><table>
                <caption>{en ? "Completed selected-condition outputs / five conditions in each cell" : "각 칸의 선택 조건 출력 완료 개수 / 조건 5개"}</caption>
                <thead><tr><th scope="col">{en ? "Attack-array origin" : "공격 배열 생성 출처"}</th><th scope="col">Windows</th><th scope="col">Linux · oneDNN=1</th></tr></thead>
                <tbody>{snapshot.attack_array_origins.map(origin => <tr key={origin}>
                    <th scope="row">{origin === "pc" ? "PC" : "Linux"}</th>
                    <td>{completed(origin, "windows_native_default")} / {snapshot.selected_conditions_per_cell}</td>
                    <td>{completed(origin, "linux_oneDNN_1")} / {snapshot.selected_conditions_per_cell}</td>
                </tr>)}</tbody>
            </table></div>
            <p className="diagnostic-note">{en
                ? "Labels matched for all 10 same-array pairs, while no probability vector was exactly identical. Changing the array origin changed all five selected labels in both scoring environments. This narrows the observed discrepancy to the saved-input comparison; it does not establish a single cause of attack-generation differences or exclude operating-system effects during generation."
                : "같은 배열의 라벨은 10쌍 모두 일치했지만 확률 벡터가 완전히 같은 쌍은 없었습니다. 배열 출처를 바꾸면 두 분류 환경 모두 선택 5조건의 라벨이 달라졌습니다. 관찰된 차이의 범위를 좁힌 결과이며, 공격 생성 차이의 단일 원인이나 생성 단계의 운영체제 영향까지 확정하지 않습니다."}</p>
            <div className="diagnostic-verdicts"><span>{en ? "External Stage B: FAIL" : "외부 Stage B: FAIL"}</span><span>{en ? "Generation cause: UNRESOLVED" : "생성 원인: UNRESOLVED"}</span></div>
            <p className="diagnostic-common">{en
                ? "Windows added two scoring processes and 10 selected outputs. The matrix's 20 outputs reuse selected images and are not 20 independent samples. No new training or attack generation; no full 781-image accuracy improvement or overall Stage B approval. This page displays saved results and starts no inference."
                : "Windows에서 분류 프로세스 2회·선택 출력 10개를 추가했습니다. 교차표의 출력 20개는 같은 선택 이미지를 반복 사용하므로 독립 표본 20개가 아닙니다. 새 학습·공격 생성은 없으며, 전체 781장 정확도 향상이나 전체 Stage B 승인을 뜻하지 않습니다. 이 화면은 저장 결과를 표시하며 추론을 실행하지 않습니다."}</p>
            <a href={details} target="_blank" rel="noreferrer">{en ? "Scope, public summary and contribution record ↗" : "검증 범위·공개 요약·기여 기록 ↗"}</a>
        </div>
    </section>;
}
