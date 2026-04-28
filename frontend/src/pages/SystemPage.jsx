import { useEffect, useState } from "react";

import client, { safeRequest } from "../api/client";
import SectionCard from "../components/layout/SectionCard";
import StatusPill from "../components/layout/StatusPill";
import StatCard from "../components/evolution/StatCard";

export default function SystemPage() {
  const [system, setSystem] = useState(null);

  useEffect(() => {
    const load = async () => {
      const { data } = await safeRequest(() => client.get("/api/system"));
      if (data) setSystem(data);
    };
    load();
    const timer = window.setInterval(load, 12000);
    return () => window.clearInterval(timer);
  }, []);

  const services = system?.services ?? {};
  const runtime = system?.runtime ?? {};
  const assets = system?.assets ?? {};

  return (
    <main className="page-shell grid-shell space-y-6">
      <section className="glass-card p-6">
        <p className="text-sm uppercase tracking-[0.35em] text-aegis-primary">System Status</p>
        <h1 className="mt-3 text-4xl font-bold">Operational health for services, assets, and monitored folders.</h1>
      </section>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="CPU" value={`${runtime.cpu_percent ?? 0}%`} accent="text-aegis-primary" />
        <StatCard label="Memory" value={`${runtime.memory_percent ?? 0}%`} accent="text-aegis-warning" />
        <StatCard label="Disk" value={`${runtime.disk_percent ?? 0}%`} accent="text-aegis-info" />
        <StatCard label="Watch Folders" value={system?.watch_folders?.length ?? 0} accent="text-aegis-success" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr,1fr]">
        <SectionCard title="Services" subtitle="Live status for the backend, Redis, watcher modules, and persistence mode.">
          <div className="grid gap-3 md:grid-cols-2">
            {Object.entries(services).map(([key, value]) => (
              <div key={key} className="rounded-2xl border border-white/10 bg-black/15 p-4">
                <p className="text-sm font-semibold capitalize">{key.replaceAll("_", " ")}</p>
                <div className="mt-3">
                  <StatusPill status={value} />
                </div>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Runtime" subtitle="Host-level runtime metadata captured for the command center.">
          <div className="space-y-3 text-sm">
            <div className="rounded-2xl border border-white/10 bg-black/15 p-4">Platform: {runtime.platform ?? "n/a"}</div>
            <div className="rounded-2xl border border-white/10 bg-black/15 p-4">Python: {runtime.python_version ?? "n/a"}</div>
            <div className="rounded-2xl border border-white/10 bg-black/15 p-4">Boot time: {runtime.boot_time ? new Date(runtime.boot_time).toLocaleString() : "n/a"}</div>
          </div>
        </SectionCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr,1fr]">
        <SectionCard title="Model Assets" subtitle="Files required for inference, explainability, and continual learning.">
          <div className="grid gap-3 md:grid-cols-2">
            {Object.entries(assets).map(([key, value]) => (
              <div key={key} className="rounded-2xl border border-white/10 bg-black/15 p-4">
                <p className="text-sm font-semibold capitalize">{key.replaceAll("_", " ")}</p>
                <div className="mt-3">
                  <StatusPill status={value ? "active" : "error"} label={value ? "present" : "missing"} />
                </div>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Watch Folder Inventory" subtitle="Current protected directories and their monitoring scope.">
          <div className="space-y-3">
            {(system?.watch_folders ?? []).map((folder) => (
              <div key={folder.path} className="rounded-2xl border border-white/10 bg-black/15 p-4">
                <p className="text-sm font-semibold">{folder.path}</p>
                <p className="mt-1 text-xs text-aegis-muted">{folder.extensions?.join(", ")}</p>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
    </main>
  );
}
