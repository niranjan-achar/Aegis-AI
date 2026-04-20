import { useEffect, useState } from "react";

import TrainingProgress from "./TrainingProgress";

const labelOptions = [
  "Benign",
  "Adialer.C",
  "Agent.FYI",
  "Allaple.A",
  "Allaple.L",
  "Alueron.gen!J",
  "Autorun.K",
  "C2LOP.gen!g",
  "C2LOP.P",
  "Dialplatform.B",
  "Dontovo.A",
  "Fakerean",
  "Instantaccess",
  "Lolyda.AA1",
  "Lolyda.AA2",
  "Lolyda.AA3",
  "Lolyda.AT",
  "Malex.gen!J",
  "Obfuscator.AD",
  "Rbot!gen",
  "Skintrim.N",
  "Swizzor.gen!E",
  "Swizzor.gen!I",
  "VB.AT",
  "Wintrim.BX",
  "Yuner.A",
];

export default function LabelPanel({ item, onConfirm, wsStatus, wsMessages }) {
  const [label, setLabel] = useState(item?.prediction ?? "Benign");

  useEffect(() => {
    setLabel(item?.prediction ?? "Benign");
  }, [item]);

  if (!item) {
    return (
      <div className="glass-card flex min-h-[360px] items-center justify-center p-6 text-center text-aegis-muted">
        Select a queued file to inspect its binary image, heatmap, and labelling controls.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="glass-card p-4">
        <h3 className="text-lg font-semibold">{item.filename}</h3>
        <p className="mt-1 text-sm text-aegis-muted">
          Current prediction: {item.prediction} ({Math.round(item.confidence * 100)}%)
        </p>
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          {item.image_b64 ? (
            <img src={`data:image/png;base64,${item.image_b64}`} alt="Binary preview" className="rounded-2xl border border-white/10" />
          ) : null}
          {item.heatmap_b64 ? (
            <img src={`data:image/png;base64,${item.heatmap_b64}`} alt="Heatmap preview" className="rounded-2xl border border-white/10" />
          ) : null}
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <select
            value={label}
            onChange={(event) => setLabel(event.target.value)}
            className="rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm"
          >
            {labelOptions.map((option) => (
              <option key={option} value={option} className="bg-aegis-surface">
                {option}
              </option>
            ))}
          </select>
          <button type="button" onClick={() => onConfirm(label)} className="glass-button bg-aegis-primary/20">
            Confirm Label
          </button>
        </div>
      </div>

      <TrainingProgress status={wsStatus} messages={wsMessages} />
    </div>
  );
}
