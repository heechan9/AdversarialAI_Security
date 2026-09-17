"use client";
import { useEffect, useRef, useState } from "react";
import { ArrowRight, ExternalLink, Info, Minus, Plus, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { type Sample } from "@/lib/evidence";
import { ko, modelName, pct } from "@/lib/display";
import { boundView, initialView, type ImageView } from "@/lib/image-view";

export function Panel({ sample, part, compact = false, viewport = initialView, onPan }: {
  sample: Sample; part: number; compact?: boolean; viewport?: ImageView;
  onPan?: (dx: number, dy: number) => void;
}) {
  const [bad, setBad] = useState(false);
  const drag = useRef<{ id: number; x: number; y: number } | null>(null);
  useEffect(() => setBad(false), [sample.asset]);
  const crop = sample.panels[part];
  const movable = !compact && viewport.zoom > 1 && !bad;
  return <div className={`image-panel ${compact ? "compact" : ""} ${movable ? "pannable" : ""}`}
    style={{ touchAction: movable ? "none" : "pan-y" }}
    onPointerDown={e => {
      if (!movable || !e.isPrimary || (e.pointerType === "mouse" && e.button !== 0)) return;
      e.currentTarget.setPointerCapture(e.pointerId);
      drag.current = { id: e.pointerId, x: e.clientX, y: e.clientY };
    }}
    onPointerMove={e => {
      const d = drag.current;
      if (!d || d.id !== e.pointerId) return;
      const rect = e.currentTarget.getBoundingClientRect();
      onPan?.((e.clientX - d.x) / rect.width, (e.clientY - d.y) / rect.height);
      drag.current = { id: d.id, x: e.clientX, y: e.clientY };
    }}
    onPointerUp={() => { drag.current = null; }}
    onPointerCancel={() => { drag.current = null; }}
    onLostPointerCapture={() => { drag.current = null; }}>
    {bad ? <div className="asset-error" role="status"><Info size={20} />이미지를 불러오지 못했습니다.<br />원본 그림 링크에서 확인해주세요.</div> :
      <div className="image-crop" style={{ transform: `translate(${viewport.x * 100}%, ${viewport.y * 100}%) scale(${viewport.zoom})` }}>
        <img src={sample.asset} draggable={false} alt={`${sample.path} · ${["정상 입력", "공격 입력", "차이 확대 표시"][part]}`}
          onError={() => setBad(true)} style={{ width: `${sample.width / crop.size * 100}%`, maxWidth: "none", left: `${-crop.x / crop.size * 100}%`, top: `${-crop.y / crop.size * 100}%` }} />
      </div>}
  </div>;
}

export default function ImageComparison({ sample }: { sample: Sample }) {
  const [tab, setTab] = useState("compare");
  const [viewport, setViewport] = useState(initialView);
  const pan = (dx: number, dy: number) => setViewport(v => boundView({ ...v, x: v.x + dx, y: v.y + dy }));
  return <article className="comparison">
    <div className="comparison-toolbar"><div><span className="model-chip">{modelName(sample.model)}</span><span>비표적 FGSM</span><span className="epsilon-chip">ε {sample.epsilon}</span></div><a href={sample.sourceUrl} target="_blank" rel="noreferrer">원본 그림 <ExternalLink size={16} /></a></div>
    <div className="case-verdict" aria-live="polite"><div><span>이 이미지의 실제 판단 변화</span><h3>{ko(sample.cleanPrediction)} <ArrowRight aria-label="에서" /> {ko(sample.attackPrediction)}</h3></div><span className={`outcome ${sample.success ? "warn" : "safe"}`}>{sample.success ? "공격 성공 · 오답 전환" : "공격 실패 · 정답 유지"}</span></div>
    <Tabs value={tab} onValueChange={setTab} className="comparison-views"><p id="view-mode-label" className="view-mode-label">보기 모드 <span>한 가지 보기를 선택하세요</span></p><TabsList aria-labelledby="view-mode-label" className="view-tabs"><TabsTrigger value="compare">나란히 비교</TabsTrigger><TabsTrigger value="clean">정상 입력</TabsTrigger><TabsTrigger value="attack">공격 입력</TabsTrigger><TabsTrigger value="delta">차이 확대 표시</TabsTrigger></TabsList><TabsContent value={tab} className="view-content">
    <div className="image-tools"><span>두 이미지 동시 확대 <b>{viewport.zoom.toFixed(1)}×</b></span><div><Button variant="outline" size="icon" aria-label="비교 이미지 축소" disabled={viewport.zoom <= 1} onClick={() => setViewport(v => boundView({ ...v, zoom: v.zoom - .5 }))}><Minus /></Button><Button variant="outline" size="icon" aria-label="비교 이미지 확대" disabled={viewport.zoom >= 3} onClick={() => setViewport(v => boundView({ ...v, zoom: v.zoom + .5 }))}><Plus /></Button><Button variant="outline" onClick={() => setViewport(initialView)}><RotateCcw size={15} /> 이미지 초기화</Button></div></div>
    <div className={`comparison-images ${tab !== "compare" ? "single" : ""}`}>{(tab === "compare" ? [0, 1] : [tab === "clean" ? 0 : tab === "attack" ? 1 : 2]).map(part => <figure key={part}><div className="figure-label"><b>{["정상 이미지", "공격 이미지", "차이 확대 표시"][part]}</b><span>{part < 2 ? `판단: ${ko(part === 0 ? sample.cleanPrediction : sample.attackPrediction)}` : "기존 실험 그림"}</span></div><Panel sample={sample} part={part} viewport={viewport} onPan={pan} /><figcaption>{part === 0 ? `모델 출력 점수 ${pct(sample.cleanScore)}` : part === 1 ? "공격 후 점수: 저장된 기록 없음" : "표시용 RGB 절대 차이 · 이미지별 최댓값 정규화"}</figcaption></figure>)}</div>
    <p className="score-help">모델 출력 점수는 모델이 선택한 답에 부여한 값입니다. <strong>실제로 정답일 확률을 뜻하지 않습니다.</strong> 공격 후 점수는 기존 기록에 저장되지 않아 표시하지 않습니다.</p>
    <p className="pan-hint">확대한 뒤 이미지를 드래그하면 같은 위치가 함께 이동합니다. 탭을 바꿔도 배율과 위치가 유지됩니다.</p>
    {viewport.zoom > 1 && <div className="pan-buttons" aria-label="두 이미지 위치 이동"><Button variant="outline" onClick={() => pan(.12, 0)} aria-label="이미지 왼쪽 부분 보기">←</Button><Button variant="outline" onClick={() => pan(0, .12)} aria-label="이미지 위쪽 부분 보기">↑</Button><Button variant="outline" onClick={() => pan(0, -.12)} aria-label="이미지 아래쪽 부분 보기">↓</Button><Button variant="outline" onClick={() => pan(-.12, 0)} aria-label="이미지 오른쪽 부분 보기">→</Button></div>}
    {tab === "delta" && <div className="difference-explainer"><h4>왜 거의 흰색으로 보일까요?</h4><p>기존 저장 코드는 <code>|공격 − 정상| ÷ 해당 이미지의 최대 절대 차이</code>를 RGB 채널에 적용했습니다. 세 채널의 차이가 모두 최댓값에 가까우면 흰색, 모두 0이면 검정으로 보입니다. FGSM에서는 차이 크기가 비슷한 픽셀이 많아 화면이 하얗게 보일 수 있습니다.</p><p>이미지별 상대 크기이며, 흰색이 공격 성공이나 AI의 주목 영역을 뜻하지 않습니다. 원본 배열이 없어 실제 최대 차이와 수치 배율은 복원하지 않았습니다. 위 {viewport.zoom.toFixed(1)}×는 화면 확대 배율일 뿐, 교란 배율이 아닙니다.</p></div>}
    </TabsContent></Tabs>
    <div className="truth-row"><span>기록된 정답 <b>{ko(sample.truth)}</b></span><code>{sample.path.split("/").pop()}</code></div>
    <p className="score-note">표시 이미지는 저장된 비교 PNG의 영역을 잘라 보여줍니다. 원본 입력 배열을 재계산한 화면이 아닙니다.</p>
  </article>;
}
