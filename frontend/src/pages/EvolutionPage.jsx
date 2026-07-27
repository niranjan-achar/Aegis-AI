import { useEffect, useMemo, useState } from "react";

import client, { safeRequest } from "../api/client";
import AccuracyChart from "../components/evolution/AccuracyChart";
import StatCard from "../components/evolution/StatCard";
import TrainingHistory from "../components/evolution/TrainingHistory";
import SectionCard from "../components/layout/SectionCard";

export default function EvolutionPage() {
  const [runs, setRuns] = useState([]);
  const [modelMetadata, setModelMetadata] = useState([]);

  const fallbackRuns = useMemo(
    () => [
      {
        version: "0.3",
        accuracy: 0.86,
        families: ["Allaple.L", "Rbot!gen", "VB.AT"],
        status: "FINISHED",
        start_time: Date.now() - 1000 * 60 * 60 * 24 * 10,
      },
      {
        version: "0.2",
        accuracy: 0.82,
        families: ["Allaple.L", "VB.AT"],
        status: "FINISHED",
        start_time: Date.now() - 1000 * 60 * 60 * 24 * 24,
      },
      {
        version: "0.1",
        accuracy: 0.78,
        families: ["VB.AT"],
        status: "FINISHED",
        start_time: Date.now() - 1000 * 60 * 60 * 24 * 45,
      },
    ],
    [],
  );

  const fallbackMetadata = useMemo(
    () => [
      {
        id: "meta-0.3",
        version: "0.3",
        dataset: "MalImg + PE features",
        trigger: "Analyst label batch",
        mean_accuracy: 0.86,
        ewc_loss: 0.0312,
        created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 10).toISOString(),
      },
      {
        id: "meta-0.2",
        version: "0.2",
        dataset: "MalImg baseline",
        trigger: "Initial training",
        mean_accuracy: 0.82,
        ewc_loss: 0.0468,
        created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 24).toISOString(),
      },
    ],
    [],
  );

  useEffect(() => {
    safeRequest(() => client.get("/api/evolution")).then(({ data }) => {
      if (data?.runs) setRuns(data.runs);
    });
    safeRequest(() => client.get("/api/models/metadata", { params: { limit: 12 } })).then(({ data }) => {
      if (data?.items) setModelMetadata(data.items);
    });
  }, []);

  const displayRuns = runs.length ? runs : fallbackRuns;
  const displayMetadata = modelMetadata.length ? modelMetadata : fallbackMetadata;

  const stats = useMemo(() => {
    const latest = displayRuns[0] ?? {};
    return {
      version: latest.version ?? "n/a",
      families: Array.from(new Set(displayRuns.flatMap((run) => run.families ?? []))).length,
      samples: displayRuns.length,
      accuracy: `${Math.round((latest.accuracy ?? 0) * 100)}%`,
    };
  }, [displayRuns]);

  return (
    <main className="page-shell space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Model Version" value={stats.version} accent="text-aegis-primary" />
        <StatCard label="Families Known" value={stats.families} accent="text-aegis-success" />
        <StatCard label="Samples Learned" value={stats.samples} accent="text-aegis-info" />
        <StatCard label="Avg Accuracy" value={stats.accuracy} accent="text-aegis-warning" />
      </div>
      <AccuracyChart runs={displayRuns} />
      <TrainingHistory runs={displayRuns} />
      <SectionCard title="Model Metadata" subtitle="Stored training summaries and dataset context.">
        <div className="space-y-3">
          {displayMetadata.length ? (
            displayMetadata.map((item) => (
              <div key={item.id ?? `${item.sha256}-${item.created_at}`} className="rounded-2xl border border-white/10 bg-black/15 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold">{item.version ?? "Model update"}</p>
                    <p className="mt-1 text-xs text-aegis-muted">
                      {item.dataset ?? "dataset"} | {item.trigger ?? "trigger"}
                    </p>
                    <p className="mt-1 text-xs text-aegis-muted">
                      accuracy {Math.round((item.mean_accuracy ?? 0) * 100)}% | loss {(item.ewc_loss ?? 0).toFixed(4)}
                    </p>
                  </div>
                  <span className="text-xs text-aegis-muted">{item.created_at ? new Date(item.created_at).toLocaleString() : "n/a"}</span>
                </div>
              </div>
            ))
          ) : (
            <p className="text-sm text-aegis-muted">No model metadata recorded yet.</p>
          )}
        </div>
      </SectionCard>
    </main>
  );
}
