import { useEffect, useMemo, useState } from "react";

import client, { API_BASE_URL, safeRequest } from "../api/client";
import SectionCard from "../components/layout/SectionCard";
import StatusPill from "../components/layout/StatusPill";
import StatCard from "../components/evolution/StatCard";
import { useToast } from "../hooks/useToast.jsx";
import { useWebSocket } from "../hooks/useWebSocket";

function formatTime(value) {
  return value ? new Date(value).toLocaleString() : "n/a";
}

export default function LiveMonitorPage() {
  const [watchers, setWatchers] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [events, setEvents] = useState([]);
  const [scans, setScans] = useState([]);
  const [watchPath, setWatchPath] = useState("");
  const { pushToast } = useToast();
  const wsUrl = useMemo(() => API_BASE_URL.replace(/^http/, "ws") + "/ws/telemetry", []);
  const { messages, status } = useWebSocket(wsUrl, true);

  const loadData = async () => {
    const [watchersRes, alertsRes, eventsRes, scansRes] = await Promise.all([
      safeRequest(() => client.get("/api/watchers")),
      safeRequest(() => client.get("/api/alerts", { params: { limit: 8 } })),
      safeRequest(() => client.get("/api/telemetry", { params: { limit: 18 } })),
      safeRequest(() => client.get("/api/scans", { params: { limit: 8 } })),
    ]);

    if (watchersRes.data?.items) setWatchers(watchersRes.data.items);
    if (alertsRes.data?.items) setAlerts(alertsRes.data.items);
    if (eventsRes.data?.items) setEvents(eventsRes.data.items);
    if (scansRes.data?.items) setScans(scansRes.data.items);
  };

  useEffect(() => {
    loadData();
    const timer = window.setInterval(loadData, 15000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const latest = messages.at(-1);
    if (!latest?.type || !latest.payload) return;
    if (latest.type === "file_created" || latest.type === "network_connection" || latest.type === "watcher_scan_failed") {
      setEvents((current) => [latest.payload, ...current].slice(0, 18));
    }
    if (latest.type === "scan_completed") {
      setScans((current) => [latest.payload, ...current].slice(0, 8));
    }
    if (latest.type === "alert_created") {
      setAlerts((current) => [latest.payload, ...current].slice(0, 8));
      pushToast({
        title: latest.payload.title ?? "Alert raised",
        message: latest.payload.summary ?? "Aegis-AI generated a live alert.",
        type: latest.payload.severity === "low" ? "info" : "error",
      });
    }
  }, [messages, pushToast]);

  const addWatchFolder = async () => {
    if (!watchPath.trim()) return;
    const { error } = await safeRequest(() =>
      client.post("/api/watchers", { path: watchPath.trim(), recursive: true }),
    );
    if (error) {
      pushToast({ title: "Watch folder failed", message: error, type: "error" });
      return;
    }
    setWatchPath("");
    await loadData();
    pushToast({ title: "Watch folder added", message: "The folder is now monitored for new suspicious files.", type: "success" });
  };

  const removeWatchFolder = async (path) => {
    const { error } = await safeRequest(() =>
      client.delete("/api/watchers", { params: { path } }),
    );
    if (error) {
      pushToast({ title: "Remove failed", message: error, type: "error" });
      return;
    }
    await loadData();
  };

  return (
    <main className="page-shell grid-shell space-y-6">
      <section className="glass-card overflow-hidden p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-[0.35em] text-aegis-primary">Live Monitor</p>
            <h1 className="mt-3 max-w-3xl text-4xl font-bold">Real-time file and network telemetry for autonomous host defense.</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-aegis-muted">
              This page correlates watched-folder events, auto-scans, outbound connections, and alert generation so the dashboard feels like a live endpoint defense console.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusPill label="Telemetry" status={status} />
            <StatusPill label={`${watchers.length} folders`} status={watchers.length ? "active" : "idle"} />
          </div>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Watched Folders" value={watchers.length} accent="text-aegis-primary" />
        <StatCard label="Live Alerts" value={alerts.length} accent="text-aegis-danger" />
        <StatCard label="Recent Events" value={events.length} accent="text-aegis-info" />
        <StatCard label="Auto Scans" value={scans.filter((scan) => scan.source === "watcher").length} accent="text-aegis-success" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[360px,1fr,360px]">
        <SectionCard
          title="Protected Folders"
          subtitle="Add Downloads, Desktop, Temp, or any other high-risk path for automatic surveillance."
          actions={
            <>
              <input
                value={watchPath}
                onChange={(event) => setWatchPath(event.target.value)}
                placeholder="D:\\Users\\You\\Downloads"
                className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm"
              />
              <button type="button" onClick={addWatchFolder} className="glass-button bg-aegis-primary/15">
                Add
              </button>
            </>
          }
        >
          <div className="space-y-3">
            {watchers.map((watcher) => (
              <div key={watcher.path} className="rounded-2xl border border-white/10 bg-black/15 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold">{watcher.path}</p>
                    <p className="mt-1 text-xs text-aegis-muted">{watcher.extensions?.join(", ")}</p>
                  </div>
                  <button type="button" onClick={() => removeWatchFolder(watcher.path)} className="text-xs text-aegis-danger">
                    Remove
                  </button>
                </div>
              </div>
            ))}
            {!watchers.length ? <p className="text-sm text-aegis-muted">No folders are being watched yet.</p> : null}
          </div>
        </SectionCard>

        <SectionCard title="Live Event Feed" subtitle="New files, network flows, failed watcher scans, and correlated telemetry arrive here first.">
          <div className="space-y-3">
            {events.map((event) => (
              <div key={event.id} className="rounded-2xl border border-white/10 bg-black/15 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold">{event.event_type.replaceAll("_", " ")}</p>
                    <p className="mt-1 text-xs text-aegis-muted">
                      {event.path ?? `${event.process_name ?? "Unknown"} -> ${event.remote_ip ?? "n/a"}:${event.remote_port ?? "n/a"}`}
                    </p>
                  </div>
                  <p className="text-xs text-aegis-muted">{formatTime(event.created_at)}</p>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>

        <div className="space-y-6">
          <SectionCard title="Active Alerts" subtitle="Correlation and rule scoring turn telemetry into analyst-facing warnings.">
            <div className="space-y-3">
              {alerts.map((alert) => (
                <div key={alert.id} className="rounded-2xl border border-white/10 bg-black/15 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold">{alert.title}</p>
                      <p className="mt-1 text-xs text-aegis-muted">{alert.summary}</p>
                    </div>
                    <StatusPill status={alert.severity} />
                  </div>
                </div>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Autonomous Scan Stream" subtitle="Watcher-triggered scans show how new files move into the analysis pipeline.">
            <div className="space-y-3">
              {scans.map((scan) => (
                <div key={`${scan.sha256}-${scan.created_at}`} className="rounded-2xl border border-white/10 bg-black/15 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold">{scan.filename}</p>
                      <p className="mt-1 text-xs text-aegis-muted">
                        {scan.prediction} | threat {scan.threat_score} | {scan.source}
                      </p>
                    </div>
                    <StatusPill status={scan.prediction === "Benign" ? "active" : "warning"} label={`${Math.round(scan.confidence * 100)}%`} />
                  </div>
                </div>
              ))}
            </div>
          </SectionCard>
        </div>
      </div>
    </main>
  );
}
