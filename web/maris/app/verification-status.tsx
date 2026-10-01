import snapshot from "../public/evidence/verification-status.json";

/** Build-time evidence snapshot; checked by verification/status_registry.py. */
export default function VerificationStatus() {
  return <div aria-label="재실행 검증 현황">
    <h3>재실행 검증 현황</h3>
    <div className="metric-grid">
      {snapshot.cards.map(card => <article className="metric" key={card.id}>
        <span>{card.title}</span>
        <h4>{card.label}</h4>
        <p>{card.detail}</p>
        <a href={card.evidence_url} target="_blank" rel="noreferrer">검증 근거 보기</a>
      </article>)}
    </div>
    <p>{snapshot.cause_note}</p>
  </div>;
}
