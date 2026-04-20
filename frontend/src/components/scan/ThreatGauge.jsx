import { animate, motion, useMotionValue, useTransform } from "framer-motion";
import { useEffect } from "react";

const radius = 60;
const circumference = 2 * Math.PI * radius;

function colorForScore(score) {
  if (score >= 70) return "text-aegis-danger";
  if (score >= 40) return "text-aegis-warning";
  return "text-aegis-success";
}

export default function ThreatGauge({ score, prediction, confidence, yaraMatches, scanTimeMs }) {
  const progress = useMotionValue(0);
  const strokeDashoffset = useTransform(progress, [0, 100], [circumference, 0]);

  useEffect(() => {
    const controls = animate(progress, score, { duration: 1.2, type: "spring", damping: 20 });
    return () => controls.stop();
  }, [progress, score]);

  return (
    <div className="glass-card grid gap-6 p-6 lg:grid-cols-[180px,1fr]">
      <div className="relative mx-auto flex h-40 w-40 items-center justify-center">
        <svg viewBox="0 0 160 160" className="h-full w-full -rotate-90">
          <circle cx="80" cy="80" r={radius} stroke="rgba(255,255,255,0.08)" strokeWidth="16" fill="transparent" />
          <motion.circle
            cx="80"
            cy="80"
            r={radius}
            stroke="currentColor"
            strokeWidth="16"
            strokeLinecap="round"
            fill="transparent"
            style={{ strokeDasharray: circumference, strokeDashoffset }}
            className={colorForScore(score)}
          />
        </svg>
        <div className="absolute text-center">
          <p className="text-4xl font-bold">{score}</p>
          <p className="text-xs uppercase tracking-[0.3em] text-aegis-muted">Threat</p>
        </div>
      </div>

      <div className="flex flex-col justify-center gap-3">
        <div className="inline-flex w-fit rounded-full bg-white/10 px-4 py-2 text-sm font-semibold">
          {prediction}
        </div>
        <div>
          <p className="text-2xl font-semibold">{Math.round(confidence * 100)}% confidence</p>
          <p className="mt-1 text-sm text-aegis-muted">
            {yaraMatches.length ? `YARA: ${yaraMatches.length} rules matched` : "No YARA match"}
          </p>
          <p className="mt-1 text-sm text-aegis-muted">Analysed in {scanTimeMs}ms</p>
        </div>
      </div>
    </div>
  );
}
