const toneByStatus = {
  open: "bg-aegis-success/15 text-aegis-success",
  active: "bg-aegis-success/15 text-aegis-success",
  online: "bg-aegis-success/15 text-aegis-success",
  configured: "bg-aegis-info/15 text-aegis-info",
  fallback_store: "bg-aegis-warning/15 text-aegis-warning",
  reconnecting: "bg-aegis-warning/15 text-aegis-warning",
  connecting: "bg-aegis-warning/15 text-aegis-warning",
  idle: "bg-white/10 text-aegis-muted",
  inactive: "bg-white/10 text-aegis-muted",
  error: "bg-aegis-danger/15 text-aegis-danger",
  offline: "bg-aegis-danger/15 text-aegis-danger",
};

export default function StatusPill({ label, status }) {
  return (
    <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${toneByStatus[status] ?? "bg-white/10 text-aegis-muted"}`}>
      {label ?? status}
    </span>
  );
}
