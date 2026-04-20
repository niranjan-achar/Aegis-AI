import { useMemo, useState } from "react";
import {
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export default function AccuracyChart({ runs }) {
  const familyNames = useMemo(
    () => Array.from(new Set(runs.flatMap((run) => run.families ?? []))).slice(0, 8),
    [runs],
  );
  const [visible, setVisible] = useState(() => Object.fromEntries(familyNames.map((name) => [name, true])));

  const chartData = runs.map((run, index) => {
    const entry = {
      name: run.version === "n/a" ? `Run ${index + 1}` : `v${run.version}`,
      accuracy: Math.round((run.accuracy ?? 0) * 100),
    };
    familyNames.forEach((family) => {
      entry[family] = Math.round((run[`acc_${family}`] ?? run.accuracy ?? 0) * 100);
    });
    return entry;
  });

  return (
    <div className="glass-card p-6">
      <h3 className="mb-4 text-xl font-semibold">Accuracy Over Time</h3>
      <div className="h-[360px]">
        <ResponsiveContainer>
          <LineChart data={chartData}>
            <XAxis dataKey="name" tick={{ fill: "#a7b0c0", fontSize: 12 }} />
            <YAxis domain={[0, 100]} tick={{ fill: "#a7b0c0", fontSize: 12 }} />
            <Tooltip
              contentStyle={{
                background: "rgba(13, 17, 23, 0.92)",
                border: "1px solid rgba(255,255,255,0.12)",
                borderRadius: "16px",
              }}
            />
            <Legend />
            <Line type="monotone" dataKey="accuracy" stroke="#6C63FF" strokeWidth={3} dot={{ r: 3 }} />
            {familyNames.map((family, index) =>
              visible[family] ? (
                <Line
                  key={family}
                  type="monotone"
                  dataKey={family}
                  stroke={["#2ED573", "#3896f5", "#f6bb4f", "#f76471", "#A78BFA", "#22d3ee", "#fb7185", "#facc15"][index % 8]}
                  strokeWidth={2}
                  dot={false}
                />
              ) : null,
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {familyNames.map((family) => (
          <button
            key={family}
            type="button"
            onClick={() => setVisible((current) => ({ ...current, [family]: !current[family] }))}
            className={`rounded-full px-3 py-1 text-xs ${visible[family] ? "bg-aegis-primary/20 text-white" : "bg-white/5 text-aegis-muted"}`}
          >
            {family}
          </button>
        ))}
      </div>
    </div>
  );
}
