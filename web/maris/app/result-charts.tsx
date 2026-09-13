"use client";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { type Evidence } from "@/lib/evidence";
import { ko, modelName } from "@/lib/display";

export default function ResultCharts({ data, className }: { data: Evidence; className: string }) {
  const series = data.epsilons.map(epsilon => {
    const row: Record<string, number | string | null> = { epsilon: String(epsilon) };
    for (const model of data.models) {
      const aggregate = data.results.find(r => r.model === model && r.epsilon === epsilon)!;
      const r = className === "all" ? aggregate : aggregate.classes.find(c => c.name === className)!;
      row[`${model}_accuracy`] = r.robustCorrect / r.n * 100;
      row[`${model}_asr`] = r.asr === null ? null : r.asr * 100;
    }
    return row;
  });
  return <section className="sweep-section" aria-label="두 모델의 공격 강도별 비교 그래프"><div className="sweep-heading"><h3>강도에 따라 두 모델을 비교해보세요.</h3><p>{className === "all" ? "전체 선박" : ko(className)} · 두 모델 · 기록된 강도 전체</p></div><div className="sweep-grid">{["accuracy", "asr"].map(metric => <figure key={metric} className="sweep-chart"><h4>{metric === "accuracy" ? "공격 후 정확도" : "공격 성공률 · ASR"}</h4><p>{metric === "accuracy" ? "분모: 선택한 클래스의 전체 표본" : "분모: 각 모델이 정상 입력에서 맞힌 표본"}</p><div className="chart-canvas"><ResponsiveContainer width="100%" height="100%"><BarChart data={series} margin={{ top: 12, right: 8, left: -16, bottom: 12 }} accessibilityLayer><CartesianGrid vertical={false} stroke="#324754" strokeDasharray="3 4" /><XAxis dataKey="epsilon" stroke="#c0d1db" tickLine={false} axisLine={false} tick={{ fontSize: 13 }} label={{ value: "공격 강도 ε", position: "insideBottom", offset: -10, fill: "#c0d1db" }} /><YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} stroke="#b7c9d3" tickLine={false} axisLine={false} tick={{ fontSize: 12 }} tickFormatter={n => `${n}%`} /><Tooltip cursor={{ fill: "#ffffff09" }} contentStyle={{ background: "#102532", border: "1px solid #57717e", borderRadius: 6, color: "#edf5f6", fontSize: 14 }} labelFormatter={label => `ε ${label}`} formatter={value => value === null ? "정의 불가" : `${Number(value).toFixed(2)}%`} /><Legend verticalAlign="top" height={38} />{data.models.map((model, i) => <Bar key={model} dataKey={`${model}_${metric}`} name={modelName(model)} fill={i === 0 ? "#92e2d0" : "#e3ad8a"} radius={[3, 3, 0, 0]} maxBarSize={28} isAnimationActive={false} />)}</BarChart></ResponsiveContainer></div><figcaption>{metric === "accuracy" ? "ε = 0은 정상 정확도와 같은 대조군입니다." : "정상 정답이 0장이면 ASR은 정의되지 않아 막대를 표시하지 않습니다."}</figcaption></figure>)}</div><p className="chart-scope">각 막대는 실제 기록 한 조건입니다. 강도 사이를 보간하지 않습니다. 위 단일 조건 카드와 달리 그래프에는 두 모델·모든 강도가 표시됩니다.</p></section>;
}
