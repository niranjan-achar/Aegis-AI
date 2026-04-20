import { useEffect, useMemo, useState } from "react";

import client, { API_BASE_URL, safeRequest } from "../api/client";
import LabelPanel from "../components/queue/LabelPanel";
import QueueList from "../components/queue/QueueList";
import { useToast } from "../hooks/useToast.jsx";
import { useWebSocket } from "../hooks/useWebSocket";

export default function QueuePage() {
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(null);
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

  useEffect(() => {
    loadQueue();
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
      <QueueList
        items={items}
        selectedSha={selected?.sha256}
        onSelect={setSelected}
        onAutoLabel={autoLabel}
      />
      <LabelPanel item={selected} onConfirm={confirmLabel} wsStatus={status} wsMessages={messages} />
    </main>
  );
}
