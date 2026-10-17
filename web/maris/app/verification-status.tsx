"use client";
import snapshot from "../public/evidence/verification-status.json";
import {useLocale} from "./locale-provider";

/** Historical build-time snapshot. Never rewrite registry evidence in the UI. */
export default function VerificationStatus() {
  const {t}=useLocale();
  return <div className="verification-snapshot" aria-label={t("보존된 재실행 검증 이력")}>
    <span className="eyebrow">HISTORICAL SNAPSHOT</span>
    <h3>{t("보존된 재실행 검증 이력")}</h3>
    <p className="snapshot-note">{t("아래 카드는 2026-09-28 PC 실행과 당시 외부 재실행의 보존 기록입니다. 현재 환경에서 모든 조건을 다시 검증했다는 뜻이 아닙니다.")}</p>
    <div className="metric-grid">
      {snapshot.cards.map(card => <article className="metric" key={card.id}>
        <span>{t(card.title)}</span>
        <h4>{t(card.label)}</h4>
        <p>{t(card.detail)}</p>
        <a href={card.evidence_url} target="_blank" rel="noreferrer">{t("검증 근거 보기")}</a>
      </article>)}
    </div>
    <p>{t(snapshot.cause_note)}</p>
    {snapshot.discrepancies.map(issue => <details className="record-table" key={issue.id}>
      <summary>{t(issue.title)} · {t(issue.label)}</summary>
      <ol>{issue.events.map((event, index) => <li key={index}><p>{t(event.note)}</p></li>)}</ol>
    </details>)}
  </div>;
}
