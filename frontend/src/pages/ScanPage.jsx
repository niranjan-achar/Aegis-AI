import { motion } from "framer-motion";
import { ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";

import client, { safeRequest } from "../api/client";
import ActionBar from "../components/scan/ActionBar";
import ConfidenceChart from "../components/scan/ConfidenceChart";
import HeatmapViewer from "../components/scan/HeatmapViewer";
import PEAccordion from "../components/scan/PEAccordion";
import ThreatGauge from "../components/scan/ThreatGauge";
import UploadZone from "../components/scan/UploadZone";
import { useSha256 } from "../hooks/useSha256";
import { useToast } from "../hooks/useToast.jsx";

function loadRecentScans() {
  try {
    return JSON.parse(localStorage.getItem("aegisRecentScans") ?? "[]");
  } catch {
    return [];
  }
}

export default function ScanPage() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [recentScans, setRecentScans] = useState(loadRecentScans);
  const [backendOffline, setBackendOffline] = useState(false);
  const { sha256, hashing, hashFile } = useSha256();
  const { pushToast } = useToast();

  useEffect(() => {
    safeRequest(() => client.get("/api/health")).then(({ error }) => setBackendOffline(Boolean(error)));
  }, []);

  const onFileSelect = async (selected) => {
    setFile(selected);
    setResult(null);
    await hashFile(selected);
  };

  const onScan = async () => {
    if (!file) return;
    setLoading(true);
    setProgress(10);
    const formData = new FormData();
    formData.append("file", file);
    const { data, error } = await safeRequest(() =>
      client.post("/api/scan", formData, {
        onUploadProgress: (event) => {
          if (!event.total) return;
          setProgress(Math.round((event.loaded / event.total) * 100));
        },
      }),
    );
    setLoading(false);

    if (error) {
      setBackendOffline(true);
      pushToast({ title: "Scan failed", message: error, type: "error" });
      return;
    }

    setBackendOffline(false);
    setResult(data);
    const nextRecent = [{ ...data, timestamp: Date.now() }, ...recentScans].slice(0, 5);
    setRecentScans(nextRecent);
    localStorage.setItem("aegisRecentScans", JSON.stringify(nextRecent));
    pushToast({
      title: "Scan complete",
      message: `${data.prediction} detected at ${Math.round(data.confidence * 100)}% confidence.`,
      type: data.prediction === "Benign" ? "success" : "info",
    });
  };

  const submitLabel = async (label) => {
    if (!result) return;
    const { error } = await safeRequest(() => client.post("/api/label", { sha256: result.sha256, label }));
    if (error) {
      pushToast({ title: "Queue update failed", message: error, type: "error" });
      return;
    }
    pushToast({ title: "Label queued", message: `Queued ${label} for continual learning.`, type: "success" });
  };

  const downloadReport = () => {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${result.sha256}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <main className="page-shell">
      <div className="grid gap-6 xl:grid-cols-[420px,1fr]">
        <UploadZone
          file={file}
          onFileSelect={onFileSelect}
          onScan={onScan}
          loading={loading}
          progress={progress}
          sha256={sha256}
          hashing={hashing}
          recentScans={recentScans}
        />

        <section className="space-y-6">
          {backendOffline ? (
            <div className="glass-card flex min-h-[320px] flex-col items-center justify-center p-8 text-center">
              <ShieldAlert className="h-14 w-14 text-aegis-warning" />
              <h2 className="mt-4 text-2xl font-semibold">Backend offline</h2>
              <p className="mt-2 max-w-md text-sm text-aegis-muted">
                The frontend is running, but the FastAPI backend is not reachable. Start `uvicorn main:app --reload --port 8000`
                in `D:\MCA-RVCE\Projects\Aegis-AI\backend`.
              </p>
            </div>
          ) : null}

          {!result && !backendOffline ? (
            <div className="glass-card flex min-h-[320px] flex-col items-center justify-center p-8 text-center">
              <ShieldAlert className="h-14 w-14 text-aegis-muted" />
              <h2 className="mt-4 text-2xl font-semibold">Upload a file to begin analysis</h2>
              <p className="mt-2 max-w-md text-sm text-aegis-muted">
                Aegis-AI will extract binary, PE, YARA, and explainability signals once the file is scanned.
              </p>
            </div>
          ) : null}

          {result ? (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
              <ThreatGauge
                score={result.threat_score}
                prediction={result.prediction}
                confidence={result.confidence}
                yaraMatches={result.yara_matches}
                scanTimeMs={result.scan_time_ms}
              />
              <HeatmapViewer
                imageB64={result.image_b64}
                heatmapB64={result.heatmap_b64}
                offsets={result.top_offsets}
              />
              <div className="grid gap-6 xl:grid-cols-2">
                <ConfidenceChart top3={result.top3} yaraMatches={result.yara_matches} />
                <PEAccordion peFeatures={result.pe_features} />
              </div>
              <ActionBar
                visible={result.confidence < 0.85}
                onConfirmMalware={() => submitLabel(result.prediction)}
                onMarkBenign={() => submitLabel("Benign")}
                onDownload={downloadReport}
              />
            </motion.div>
          ) : null}
        </section>
      </div>
    </main>
  );
}
