export default function ActionBar({ visible, onConfirmMalware, onMarkBenign, onDownload }) {
  if (!visible) {
    return null;
  }

  return (
    <div className="glass-card flex flex-wrap gap-3 p-4">
      <button type="button" onClick={onConfirmMalware} className="glass-button bg-aegis-danger/20">
        Confirm as Malware
      </button>
      <button type="button" onClick={onMarkBenign} className="glass-button bg-aegis-success/20">
        Mark as Benign
      </button>
      <button type="button" onClick={onDownload} className="glass-button">
        Download Report
      </button>
    </div>
  );
}
