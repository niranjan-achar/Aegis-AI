import { useEffect, useMemo, useState } from "react";

import client, { safeRequest } from "../api/client";
import AccuracyChart from "../components/evolution/AccuracyChart";
import StatCard from "../components/evolution/StatCard";
import TrainingHistory from "../components/evolution/TrainingHistory";

export default function EvolutionPage() {
  const [runs, setRuns] = useState([]);

  useEffect(() => {
    safeRequest(() => client.get("/api/evolution")).then(({ data }) => {
      if (data?.runs) setRuns(data.runs);
    });
  }, []);

  const stats = useMemo(() => {
    const latest = runs[0] ?? {};
    return {
      version: latest.version ?? "n/a",
      families: Array.from(new Set(runs.flatMap((run) => run.families ?? []))).length,
      samples: runs.length,
      accuracy: `${Math.round((latest.accuracy ?? 0) * 100)}%`,
    };
  }, [runs]);

  return (
    <main className="page-shell space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Model Version" value={stats.version} accent="text-aegis-primary" />
        <StatCard label="Families Known" value={stats.families} accent="text-aegis-success" />
        <StatCard label="Samples Learned" value={stats.samples} accent="text-aegis-info" />
        <StatCard label="Avg Accuracy" value={stats.accuracy} accent="text-aegis-warning" />
      </div>
      <AccuracyChart runs={runs} />
      <TrainingHistory runs={runs} />
    </main>
  );
}
