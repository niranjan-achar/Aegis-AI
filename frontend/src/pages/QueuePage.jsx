import { useEffect, useMemo, useState } from "react";

import client, { API_BASE_URL, safeRequest } from "../api/client";
import SectionCard from "../components/layout/SectionCard";
import StatusPill from "../components/layout/StatusPill";
import LabelPanel from "../components/queue/LabelPanel";
import QueueList from "../components/queue/QueueList";
import { useToast } from "../hooks/useToast.jsx";
import { useWebSocket } from "../hooks/useWebSocket";

export default function QueuePage() {
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(null);
  const [labelActions, setLabelActions] = useState([]);
  const { pushToast } = useToast();
  const wsUrl = useMemo(() => API_BASE_URL.replace(/^http/, "ws") + "/ws/training", []);
  const { messages, status } = useWebSocket(wsUrl, true);

  const loadQueue = async () => {
    const { data, error } = await safeRequest(() => client.get("/api/queue"));
    if (error) {
      pushToast({ title: "Queue unavailable", message: error, type: "error" });
      return;
    }
    setItems(data.items ?? []);
    setSelected((current) => current ?? data.items?.[0] ?? null);
  };

  const loadLabelActions = async () => {
    const { data, error } = await safeRequest(() => client.get("/api/labels/actions", { params: { limit: 12 } }));
    if (error) {
      return;
    }
    setLabelActions(data.items ?? []);
  };

  useEffect(() => {
    loadQueue();
    loadLabelActions();
  }, []);

  const confirmLabel = async (label, target = selected) => {
    if (!target) return;
    const { error } = await safeRequest(() =>
      client.post("/api/label", { sha256: target.sha256, label }),
    );
    if (error) {
      pushToast({ title: "Labelling failed", message: error, type: "error" });
      return;
    }
    pushToast({ title: "Training started", message: `Queued ${label} for EWC fine-tuning.`, type: "success" });
  };

  const autoLabel = async () => {
    const candidate = items.find((item) => item.yara_confidence > 0.9);
    if (!candidate) {
      pushToast({ title: "No auto-label candidate", message: "No queued item currently has YARA confidence above 0.9.", type: "info" });
      return;
    }
    await confirmLabel(candidate.prediction, candidate);
  };

  return (
    <main className="page-shell grid gap-6 xl:grid-cols-[360px,1fr]">
      <div className="space-y-6">
        <QueueList
          items={items}
          selectedSha={selected?.sha256}
          onSelect={setSelected}
          onAutoLabel={autoLabel}
        />
        <SectionCard title="Label Actions" subtitle="Recent analyst confirmations stored in the database.">
          <div className="space-y-3">
            {labelActions.length ? (
              labelActions.map((action) => (
                <div key={action.id} className="rounded-2xl border border-white/10 bg-black/15 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold" title={action.filename ?? action.sha256}>
                        {action.filename ?? action.sha256}
                      </p>
                      <p className="mt-1 text-xs text-aegis-muted">
                        {action.label} | {Math.round((action.confidence ?? 0) * 100)}%
                      </p>
                    </div>
                    <StatusPill status="active" label={new Date(action.created_at).toLocaleString()} />
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-aegis-muted">No labels recorded yet.</p>
            )}
          </div>
        </SectionCard>
      </div>
      <LabelPanel item={selected} onConfirm={confirmLabel} wsStatus={status} wsMessages={messages} />
    </main>
  );
}
