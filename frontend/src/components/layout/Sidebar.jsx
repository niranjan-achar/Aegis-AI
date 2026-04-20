import { motion } from "framer-motion";
import { Activity, Info, ListChecks, Shield } from "lucide-react";
import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "Scan", icon: Shield },
  { to: "/evolution", label: "Evolution", icon: Activity },
  { to: "/queue", label: "Queue", icon: ListChecks },
  { to: "/about", label: "About", icon: Info },
];

export default function Sidebar() {
  return (
    <>
      <motion.aside
        initial={{ width: 72 }}
        whileHover={{ width: 220 }}
        className="glass-card fixed left-4 top-4 z-40 hidden h-[calc(100vh-2rem)] overflow-hidden p-4 md:flex md:flex-col"
      >
        <div className="mb-10 flex items-center gap-3">
          <div className="rounded-2xl bg-aegis-primary/20 p-3 text-aegis-primary">
            <Shield className="h-5 w-5" />
          </div>
          <div>
            <p className="text-lg font-bold tracking-[0.2em] text-aegis-primary">AEGIS</p>
            <p className="text-xs uppercase tracking-[0.3em] text-aegis-muted">AI</p>
          </div>
        </div>

        <nav className="flex flex-1 flex-col gap-2">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-2xl px-4 py-3 transition ${
                  isActive ? "bg-aegis-primary/20 text-white" : "text-aegis-muted hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <Icon className="h-5 w-5 shrink-0" />
              <span className="whitespace-nowrap text-sm font-medium">{label}</span>
            </NavLink>
          ))}
        </nav>
      </motion.aside>

      <nav className="glass-card fixed bottom-4 left-4 right-4 z-40 flex justify-around p-2 md:hidden">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex flex-col items-center gap-1 rounded-xl px-3 py-2 text-xs ${
                isActive ? "bg-aegis-primary/20 text-white" : "text-aegis-muted"
              }`
            }
          >
            <Icon className="h-4 w-4" />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </>
  );
}
