export default function OffsetTable({ offsets }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-white/10">
      <table className="min-w-full text-sm">
        <thead className="bg-white/5 text-left text-aegis-muted">
          <tr>
            <th className="px-4 py-3">Rank</th>
            <th className="px-4 py-3">Hex Offset</th>
            <th className="px-4 py-3">PE Section</th>
            <th className="px-4 py-3">Importance</th>
          </tr>
        </thead>
        <tbody>
          {offsets.map((item, index) => (
            <tr key={`${item.offset_hex}-${index}`} className="border-t border-white/10">
              <td className="px-4 py-3">{index + 1}</td>
              <td className="px-4 py-3 font-mono text-xs">{item.offset_hex}</td>
              <td className="px-4 py-3">{item.section}</td>
              <td className="px-4 py-3">
                <div className="h-2 rounded-full bg-white/10">
                  <div
                    className="h-2 rounded-full bg-aegis-primary"
                    style={{ width: `${Math.max(item.importance * 100, 4)}%` }}
                  />
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
