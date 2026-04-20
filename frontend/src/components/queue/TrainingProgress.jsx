export default function TrainingProgress({ status, messages }) {
  const latestEpoch = [...messages].reverse().find((message) => message.event === "training_epoch");
  const percent = latestEpoch ? (latestEpoch.epoch / latestEpoch.total_epochs) * 100 : 0;

  return (
    <div className="glass-card p-4">
      <div className="mb-3 flex items-center justify-between text-sm">
        <span>Training Progress</span>
        <span className="text-aegis-muted">{status}</span>
      </div>
      <div className="h-3 rounded-full bg-white/10">
        <div className="h-3 rounded-full bg-aegis-primary" style={{ width: `${percent}%` }} />
      </div>
      <div className="mt-4 max-h-56 space-y-2 overflow-y-auto rounded-2xl bg-black/20 p-3 font-mono text-xs text-aegis-muted">
        {messages.length ? (
          messages.map((message, index) => (
            <p key={`${message.event}-${index}`}>{JSON.stringify(message)}</p>
          ))
        ) : (
          <p>No training messages yet.</p>
        )}
      </div>
    </div>
  );
}
