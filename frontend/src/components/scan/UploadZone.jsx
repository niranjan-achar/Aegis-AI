import { motion } from "framer-motion";
import { Shield, UploadCloud } from "lucide-react";
import { useDropzone } from "react-dropzone";

function formatBytes(size) {
  if (!size) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(size) / Math.log(1024)), units.length - 1);
  return `${(size / 1024 ** index).toFixed(index === 0 ? 0 : 2)} ${units[index]}`;
}

export default function UploadZone({
  file,
  onFileSelect,
  onScan,
  loading,
  progress,
  sha256,
  hashing,
  recentScans,
}) {
  const dropzone = useDropzone({
    accept: {
      "application/vnd.microsoft.portable-executable": [".exe", ".dll"],
      "application/x-msdownload": [".exe", ".dll"],
    },
    maxSize: 20 * 1024 * 1024,
    multiple: false,
    onDropAccepted: (acceptedFiles) => onFileSelect(acceptedFiles[0]),
  });

  return (
    <div className="flex h-full flex-col gap-4">
      <div
        {...dropzone.getRootProps()}
        className="glass-card relative flex min-h-[420px] cursor-pointer flex-col items-center justify-center overflow-hidden border border-dashed border-aegis-primary/40 p-8 text-center transition hover:border-aegis-primary/80"
      >
        <input {...dropzone.getInputProps()} />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(108,99,255,0.15),transparent_45%)]" />
        <div className="relative z-10 flex flex-col items-center">
          <div className="mb-6 rounded-full bg-aegis-primary/15 p-5 text-aegis-primary shadow-[0_0_30px_rgba(108,99,255,0.35)]">
            {file ? <UploadCloud className="h-10 w-10" /> : <Shield className="h-10 w-10" />}
          </div>
          <h2 className="text-2xl font-semibold">Drop .exe or .dll here</h2>
          <p className="mt-2 text-sm text-aegis-muted">or click to browse</p>
          <p className="mt-1 text-xs uppercase tracking-[0.3em] text-aegis-muted">Max 20MB</p>

          {file ? (
            <div className="mt-8 w-full rounded-2xl border border-white/10 bg-black/20 p-4 text-left">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="truncate font-medium">{file.name}</p>
                  <p className="text-sm text-aegis-muted">{formatBytes(file.size)}</p>
                </div>
                <span className="rounded-full bg-aegis-primary/15 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-aegis-primary">
                  {file.name.split(".").pop()}
                </span>
              </div>
              <p className="mt-3 font-mono text-xs text-aegis-muted break-all">
                {hashing ? "Computing SHA-256..." : sha256 || "SHA-256 pending"}
              </p>
            </div>
          ) : null}
        </div>
      </div>

      {loading ? (
        <div className="glass-card p-4">
          <div className="mb-2 flex items-center justify-between text-sm text-aegis-muted">
            <span>Uploading and scanning</span>
            <span>{progress}%</span>
          </div>
          <div className="h-3 overflow-hidden rounded-full bg-white/5">
            <motion.div
              className="h-full rounded-full bg-aegis-primary"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
            />
          </div>
        </div>
      ) : (
        <motion.button
          whileHover={{ scale: file ? 1.02 : 1 }}
          whileTap={{ scale: file ? 0.98 : 1 }}
          type="button"
          onClick={onScan}
          disabled={!file}
          className="h-12 rounded-xl bg-aegis-primary text-sm font-semibold text-white shadow-[0_0_24px_rgba(108,99,255,0.35)] transition disabled:cursor-not-allowed disabled:bg-white/10 disabled:text-aegis-muted"
        >
          Scan File
        </motion.button>
      )}

      <div className="glass-card p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold">Recent scans</h3>
          <span className="text-xs text-aegis-muted">Local only</span>
        </div>
        <div className="space-y-3">
          {recentScans.length ? (
            recentScans.map((scan) => (
              <div key={`${scan.sha256}-${scan.scan_time_ms}`} className="rounded-2xl border border-white/10 bg-white/5 p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="truncate text-sm font-medium">{scan.filename}</p>
                  <span className="rounded-full bg-white/10 px-2 py-1 text-xs">{scan.threat_score}</span>
                </div>
                <p className="mt-1 text-xs text-aegis-muted">{new Date(scan.timestamp).toLocaleString()}</p>
              </div>
            ))
          ) : (
            <p className="text-sm text-aegis-muted">No scans yet. Your last 5 results will appear here.</p>
          )}
        </div>
      </div>
    </div>
  );
}
