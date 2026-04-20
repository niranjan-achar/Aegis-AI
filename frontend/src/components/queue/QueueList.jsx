export default function QueueList({ items, selectedSha, onSelect, onAutoLabel }) {
  return (
    <div className="glass-card p-4">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold">Pending Files</h3>
        <button type="button" onClick={onAutoLabel} className="glass-button px-3 py-2 text-xs">
          Auto-label via YARA
        </button>
      </div>
      <div className="space-y-3">
        {items.length ? (
          items.map((item) => (
            <button
              key={item.sha256}
              type="button"
              onClick={() => onSelect(item)}
              className={`w-full rounded-2xl border p-4 text-left transition ${
                selectedSha === item.sha256 ? "border-aegis-primary bg-aegis-primary/10" : "border-white/10 bg-white/5"
              }`}
            >
              <p className="truncate font-medium">{item.filename}</p>
              <p className="mt-1 text-sm text-aegis-muted">
                {item.prediction} ({Math.round(item.confidence * 100)}%)
              </p>
              <p className="mt-2 text-xs text-aegis-muted">{new Date(item.queued_at * 1000).toLocaleString()}</p>
            </button>
          ))
        ) : (
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-center">
            <p className="text-sm text-aegis-muted">
              No files awaiting review. The model is confident in all recent scans.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
