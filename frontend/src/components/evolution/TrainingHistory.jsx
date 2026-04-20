export default function TrainingHistory({ runs }) {
  return (
    <div className="glass-card overflow-hidden p-6">
      <h3 className="mb-4 text-xl font-semibold">Training History</h3>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="text-left text-aegis-muted">
            <tr>
              <th className="px-3 py-2">Version</th>
              <th className="px-3 py-2">Date</th>
              <th className="px-3 py-2">Trigger</th>
              <th className="px-3 py-2">Accuracy</th>
              <th className="px-3 py-2">EWC Loss</th>
              <th className="px-3 py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.run_id} className="border-t border-white/10 hover:bg-white/5">
                <td className="px-3 py-3">{run.version}</td>
                <td className="px-3 py-3">{run.start_time ? new Date(run.start_time).toLocaleString() : "n/a"}</td>
                <td className="px-3 py-3">{run.trigger}</td>
                <td className="px-3 py-3">{Math.round((run.accuracy ?? 0) * 100)}%</td>
                <td className="px-3 py-3">{(run.ewc_loss ?? 0).toFixed(4)}</td>
                <td className="px-3 py-3">
                  <span className={`rounded-full px-3 py-1 text-xs ${run.status === "FINISHED" ? "bg-aegis-success/15 text-aegis-success" : "bg-aegis-danger/15 text-aegis-danger"}`}>
                    {run.status === "FINISHED" ? "DEPLOYED" : "REJECTED"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
