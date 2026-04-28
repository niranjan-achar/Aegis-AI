export default function AboutPage() {
  return (
    <main className="page-shell grid-shell">
      <div className="glass-card max-w-5xl p-8">
        <p className="text-sm uppercase tracking-[0.3em] text-aegis-primary">Aegis-AI</p>
        <h1 className="mt-4 text-4xl font-bold">AI-driven, explainable malware defense with live monitoring and continual evolution</h1>
        <p className="mt-4 text-base leading-7 text-aegis-muted">
          Aegis-AI combines binary visualisation, PE-header intelligence, byte n-gram statistics, ONNX inference,
          Grad-CAM explainability, YARA signatures, watch-folder surveillance, host telemetry, and continual learning with Elastic Weight Consolidation.
        </p>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
            <h2 className="text-lg font-semibold">What makes it different</h2>
            <p className="mt-3 text-sm leading-6 text-aegis-muted">
              The platform does not rely only on signature matching. It learns structural and visual malware patterns, blends YARA evidence, and streams analyst-facing alerts in real time.
            </p>
          </div>
          <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
            <h2 className="text-lg font-semibold">SOC-style dashboard</h2>
            <p className="mt-3 text-sm leading-6 text-aegis-muted">
              Scan, Live Monitor, Analytics, Evolution, Queue, Network, Incidents, and System pages create a fuller final-year-project story around host defense operations.
            </p>
          </div>
          <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
            <h2 className="text-lg font-semibold">Student-friendly workflow</h2>
            <p className="mt-3 text-sm leading-6 text-aegis-muted">
              Local development happens on Windows 11 with Conda, Docker Desktop, FastAPI, React, and Google Colab for GPU training. The project stays realistic for a single student machine.
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
