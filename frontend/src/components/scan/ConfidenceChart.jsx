import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function ConfidenceChart({ top3, yaraMatches }) {
  const chartData = top3.map((item) => ({
    family: item.family,
    score: Math.round(item.score * 100),
  }));

  return (
    <div className="glass-card p-6">
      <h3 className="mb-4 text-xl font-semibold">Confidence Breakdown</h3>
      <div className="h-64">
        <ResponsiveContainer>
          <BarChart data={chartData} layout="vertical">
            <XAxis type="number" hide domain={[0, 100]} />
            <YAxis type="category" dataKey="family" width={120} tick={{ fill: "#fff", fontSize: 12 }} />
            <Tooltip
              contentStyle={{
                background: "rgba(13, 17, 23, 0.92)",
                border: "1px solid rgba(255,255,255,0.12)",
                borderRadius: "16px",
              }}
            />
            <Bar dataKey="score" fill="#6C63FF" radius={[8, 8, 8, 8]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-4 space-y-3">
        <h4 className="text-sm font-semibold uppercase tracking-[0.2em] text-aegis-muted">YARA matches</h4>
        {yaraMatches.length ? (
          yaraMatches.map((match) => (
            <details key={match.rule} className="rounded-2xl border border-white/10 bg-white/5 p-3">
              <summary className="cursor-pointer text-sm font-medium">{match.rule}</summary>
              <p className="mt-2 font-mono text-xs text-aegis-muted">
                {(match.matched_strings ?? []).join(", ") || "No string identifiers returned"}
              </p>
            </details>
          ))
        ) : (
          <p className="text-sm text-aegis-muted">No YARA rules matched this file.</p>
        )}
      </div>
    </div>
  );
}
