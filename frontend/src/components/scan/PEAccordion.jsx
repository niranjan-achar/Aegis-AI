export default function PEAccordion({ peFeatures }) {
  const imports = peFeatures.imports ?? {};

  return (
    <div className="glass-card p-6">
      <h3 className="mb-4 text-xl font-semibold">PE Details</h3>
      <div className="space-y-3">
        <details className="rounded-2xl border border-white/10 bg-white/5 p-4" open>
          <summary className="cursor-pointer font-medium">Sections</summary>
          <div className="mt-4 space-y-3">
            {(peFeatures.sections ?? []).map((section) => (
              <div key={`${section.name}-${section.raw_size}`} className="rounded-2xl border border-white/10 p-3">
                <div className="flex items-center justify-between">
                  <p className="font-medium">{section.name}</p>
                  <p className="text-sm text-aegis-muted">{section.raw_size} bytes</p>
                </div>
                <div className="mt-2 h-2 rounded-full bg-white/10">
                  <div
                    className={`h-2 rounded-full ${
                      section.entropy > 7 ? "bg-aegis-danger" : section.entropy > 5 ? "bg-aegis-warning" : "bg-aegis-success"
                    }`}
                    style={{ width: `${Math.min((section.entropy / 8) * 100, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </details>

        <details className="rounded-2xl border border-white/10 bg-white/5 p-4">
          <summary className="cursor-pointer font-medium">Imports</summary>
          <div className="mt-4 space-y-4">
            {Object.keys(imports).length ? (
              Object.entries(imports).map(([dll, functions]) => (
                <div key={dll}>
                  <p className="text-sm font-semibold text-aegis-info">{dll}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {functions.map((name) => (
                      <span key={name} className="rounded-full bg-white/10 px-3 py-1 text-xs">
                        {name}
                      </span>
                    ))}
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-aegis-muted">No import table available.</p>
            )}
          </div>
        </details>

        <details className="rounded-2xl border border-white/10 bg-white/5 p-4">
          <summary className="cursor-pointer font-medium">Header Flags</summary>
          <pre className="mt-4 overflow-x-auto rounded-2xl bg-black/20 p-4 text-xs text-aegis-muted">
            {JSON.stringify(peFeatures.header_flags ?? {}, null, 2)}
          </pre>
        </details>
      </div>
    </div>
  );
}
