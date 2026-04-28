import { useEffect, useState } from "react";

import client, { safeRequest } from "../api/client";
import SectionCard from "../components/layout/SectionCard";
import StatusPill from "../components/layout/StatusPill";
import StatCard from "../components/evolution/StatCard";

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState([]);
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    const load = async () => {
      const [incidentsRes, alertsRes] = await Promise.all([
        safeRequest(() => client.get("/api/incidents", { params: { limit: 20 } })),
        safeRequest(() => client.get("/api/alerts", { params: { limit: 20 } })),
      ]);
      if (incidentsRes.data?.items) setIncidents(incidentsRes.data.items);
      if (alertsRes.data?.items) setAlerts(alertsRes.data.items);
    };
    load();
    const timer = window.setInterval(load, 15000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <main className="page-shell grid-shell space-y-6">
      <section className="glass-card p-6">
        <p className="text-sm uppercase tracking-[0.35em] text-aegis-primary">Incidents</p>
        <h1 className="mt-3 text-4xl font-bold">Correlated cases built from scans, watcher events, and network-driven alerts.</h1>
      </section>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Open Cases" value={incidents.length} accent="text-aegis-warning" />
        <StatCard label="Recent Alerts" value={alerts.length} accent="text-aegis-danger" />
        <StatCard label="High/Critical" value={alerts.filter((item) => ["high", "critical"].includes(item.severity)).length} accent="text-aegis-primary" />
        <StatCard label="Correlated Assets" value={incidents.filter((item) => item.sha256).length} accent="text-aegis-info" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.2fr,0.8fr]">
        <SectionCard title="Incident Queue" subtitle="Each incident groups related alerts by file hash or affected entity.">
          <div className="space-y-4">
            {incidents.map((incident) => (
              <article key={incident.id} className="rounded-3xl border border-white/10 bg-black/15 p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-lg font-semibold">{incident.title}</p>
                    <p className="mt-2 text-sm text-aegis-muted">{incident.summary}</p>
                    <p className="mt-2 font-mono text-xs text-aegis-muted">{incident.sha256 ?? incident.entity_key}</p>
                  </div>
                  <StatusPill status={incident.severity} />
                </div>
                <div className="mt-4 flex flex-wrap gap-4 text-sm text-aegis-muted">
                  <span>Alerts: {incident.alert_count}</span>
                  <span>First seen: {incident.first_seen ? new Date(incident.first_seen).toLocaleString() : "n/a"}</span>
                  <span>Last seen: {incident.last_seen ? new Date(incident.last_seen).toLocaleString() : "n/a"}</span>
                </div>
              </article>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Alert Timeline" subtitle="Recent warnings emitted by the rule engine and telemetry correlator.">
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
                <p className="mt-3 text-xs text-aegis-muted">
                  {alert.reasons?.join(" | ") ?? "No supporting reasons captured."}
                </p>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
    </main>
  );
}
