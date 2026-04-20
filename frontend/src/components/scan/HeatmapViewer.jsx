import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";

import OffsetTable from "./OffsetTable";

export default function HeatmapViewer({ imageB64, heatmapB64, offsets }) {
  const [mode, setMode] = useState("split");

  const imageUrl = `data:image/png;base64,${imageB64}`;
  const heatmapUrl = `data:image/png;base64,${heatmapB64}`;

  return (
    <div className="glass-card p-6">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h3 className="text-xl font-semibold">Binary Heatmap Visualiser</h3>
        <div className="flex rounded-full bg-white/5 p-1 text-sm">
          {["split", "raw", "heatmap"].map((entry) => (
            <button
              key={entry}
              type="button"
              onClick={() => setMode(entry)}
              className={`rounded-full px-3 py-1 capitalize ${mode === entry ? "bg-aegis-primary/20 text-white" : "text-aegis-muted"}`}
            >
              {entry}
            </button>
          ))}
        </div>
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={mode}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className={`grid gap-4 ${mode === "split" ? "lg:grid-cols-2" : ""}`}
        >
          {(mode === "split" || mode === "raw") && (
            <div className="rounded-2xl border border-white/10 bg-black/20 p-3">
              <p className="mb-3 text-sm text-aegis-muted">Raw binary image</p>
              <img src={imageUrl} alt="Binary visualisation" className="w-full rounded-xl object-cover" />
            </div>
          )}
          {(mode === "split" || mode === "heatmap") && (
            <div className="rounded-2xl border border-white/10 bg-black/20 p-3">
              <p className="mb-3 text-sm text-aegis-muted">Grad-CAM overlay</p>
              <img src={heatmapUrl} alt="Grad-CAM overlay" className="w-full rounded-xl object-cover" />
            </div>
          )}
        </motion.div>
      </AnimatePresence>

      <div className="mt-6">
        <h4 className="mb-3 text-sm font-semibold uppercase tracking-[0.2em] text-aegis-muted">
          Top suspicious regions
        </h4>
        <OffsetTable offsets={offsets} />
      </div>
    </div>
  );
}
