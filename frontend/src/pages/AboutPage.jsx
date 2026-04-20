export default function AboutPage() {
  return (
    <main className="page-shell">
      <div className="glass-card max-w-4xl p-8">
        <p className="text-sm uppercase tracking-[0.3em] text-aegis-primary">Aegis-AI</p>
        <h1 className="mt-4 text-4xl font-bold">AI-driven, explainable malware family detection</h1>
        <p className="mt-4 text-base leading-7 text-aegis-muted">
          Aegis-AI combines binary visualisation, PE-header intelligence, byte n-gram statistics, ONNX inference,
          Grad-CAM explainability, YARA signatures, and continual learning with Elastic Weight Consolidation.
        </p>
        <div className="mt-8 grid gap-4 md:grid-cols-2">
          <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
            <h2 className="text-lg font-semibold">What makes it different</h2>
            <p className="mt-3 text-sm leading-6 text-aegis-muted">
              The platform does not rely only on signature matching. It learns structural and visual malware patterns
              and can improve itself with supervised confirmations from the review queue.
            </p>
          </div>
          <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
            <h2 className="text-lg font-semibold">Student-friendly workflow</h2>
            <p className="mt-3 text-sm leading-6 text-aegis-muted">
              Local development happens on Windows 11 with Conda, Docker Desktop, FastAPI, React, and Google Colab for
              GPU training. The guides explain each manual step in plain language.
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
