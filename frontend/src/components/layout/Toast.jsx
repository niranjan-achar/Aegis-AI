import { AnimatePresence, motion } from "framer-motion";

const borderByType = {
  success: "border-aegis-success/60",
  error: "border-aegis-danger/60",
  info: "border-aegis-primary/60",
};

export default function Toast({ toasts, dismissToast }) {
  return (
    <div className="fixed bottom-20 right-4 z-50 flex w-[min(360px,calc(100vw-2rem))] flex-col gap-3">
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.button
            key={toast.id}
            type="button"
            onClick={() => dismissToast(toast.id)}
            initial={{ opacity: 0, x: 100 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 100 }}
            className={`glass-card border p-4 text-left ${borderByType[toast.type] ?? borderByType.info}`}
          >
            <p className="text-sm font-semibold">{toast.title}</p>
            <p className="mt-1 text-sm text-aegis-muted">{toast.message}</p>
          </motion.button>
        ))}
      </AnimatePresence>
    </div>
  );
}
