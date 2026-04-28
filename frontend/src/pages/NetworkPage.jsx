import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import client, { API_BASE_URL, safeRequest } from "../api/client";
import SectionCard from "../components/layout/SectionCard";
import StatusPill from "../components/layout/StatusPill";
import StatCard from "../components/evolution/StatCard";
import { useWebSocket } from "../hooks/useWebSocket";

export default function NetworkPage() {
  const [snapshot, setSnapshot] = useState({ connections: [], top_processes: [], top_ports: [] });
  const wsUrl = useMemo(() => API_BASE_URL.replace(/^http/, "ws") + "/ws/telemetry", []);
  const { messages, status } = useWebSocket(wsUrl, true);

  const load = async () => {
    const { data } = await safeRequest(() => client.get("/api/network", { params: { limit: 80 } }));
    if (data) setSnapshot(data);
  };

  useEffect(() => {
    load();
    const timer = window.setInterval(load, 12000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const latest = messages.at(-1);
    if (latest?.type === "network_connection" && latest.payload) {
      setSnapshot((current) => ({
        ...current,
        connections: [latest.payload, ...current.connections].slice(0, 80),
      }));
    }
  }, [messages]);

  return (
    <main className="page-shell grid-shell space-y-6">
      <section className="glass-card p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-[0.35em] text-aegis-primary">Network Telemetry</p>
            <h1 className="mt-3 text-4xl font-bold">Process-linked outbound connection monitoring without overclaiming payload visibility.</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-aegis-muted">
              This view focuses on host-level network metadata, process correlation, uncommon ports, and suspicious connection patterns that can indicate adaptive or command-driven malware activity.
            </p>
          </div>
          <StatusPill label="Telemetry socket" status={status} />
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Connections" value={snapshot.connections.length} accent="text-aegis-primary" />
        <StatCard label="Processes" value={new Set(snapshot.connections.map((item) => item.process_name)).size} accent="text-aegis-info" />
        <StatCard label="Ports" value={new Set(snapshot.connections.map((item) => item.remote_port)).size} accent="text-aegis-warning" />
        <StatCard label="External Flows" value={snapshot.connections.filter((item) => item.remote_ip && item.remote_ip !== "127.0.0.1").length} accent="text-aegis-danger" />
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard title="Top Processes" subtitle="Which processes are creating the most observed outbound connection events.">
          <MiniBarChart data={snapshot.top_processes} xKey="process" />
        </SectionCard>
        <SectionCard title="Top Remote Ports" subtitle="Port frequency helps highlight beaconing on uncommon destinations.">
          <MiniBarChart data={snapshot.top_ports} xKey="port" />
        </SectionCard>
      </div>

      <SectionCard title="Recent Connections" subtitle="Metadata only: process, endpoint, port, and socket status.">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="text-left text-aegis-muted">
              <tr>
                <th className="px-3 py-2">Process</th>
                <th className="px-3 py-2">PID</th>
                <th className="px-3 py-2">Destination</th>
                <th className="px-3 py-2">Port</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Time</th>
              </tr>
            </thead>
            <tbody>
              {snapshot.connections.map((item) => (
                <tr key={item.id} className="border-t border-white/10">
                  <td className="px-3 py-3">{item.process_name}</td>
                  <td className="px-3 py-3">{item.pid}</td>
                  <td className="px-3 py-3 font-mono text-xs">{item.remote_ip}</td>
                  <td className="px-3 py-3">{item.remote_port}</td>
                  <td className="px-3 py-3">{item.status}</td>
                  <td className="px-3 py-3 text-aegis-muted">{item.created_at ? new Date(item.created_at).toLocaleTimeString() : "n/a"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </main>
  );
}

function MiniBarChart({ data, xKey }) {
  return (
    <div className="h-72">
      <ResponsiveContainer>
        <BarChart data={data}>
          <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
          <XAxis dataKey={xKey} tick={{ fill: "#d6e2ef", fontSize: 11 }} interval={0} angle={data.length > 4 ? -20 : 0} textAnchor="end" height={60} />
          <YAxis tick={{ fill: "#d6e2ef", fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey="count" fill="#47c0ff" radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
