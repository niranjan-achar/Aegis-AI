import { motion } from "framer-motion";

export default function StatCard({ label, value, accent }) {
  return (
    <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} className="glass-card p-5">
      <p className="text-sm text-aegis-muted">{label}</p>
      <p className={`mt-3 text-3xl font-bold ${accent}`}>{value}</p>
    </motion.div>
  );
}
