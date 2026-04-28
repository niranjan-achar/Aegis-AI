import { Route, Routes } from "react-router-dom";

import Sidebar from "./components/layout/Sidebar";
import Toast from "./components/layout/Toast";
import { useToast } from "./hooks/useToast.jsx";
import AnalyticsPage from "./pages/AnalyticsPage";
import AboutPage from "./pages/AboutPage";
import EvolutionPage from "./pages/EvolutionPage";
import IncidentsPage from "./pages/IncidentsPage";
import LiveMonitorPage from "./pages/LiveMonitorPage";
import NetworkPage from "./pages/NetworkPage";
import QueuePage from "./pages/QueuePage";
import ScanPage from "./pages/ScanPage";
import SystemPage from "./pages/SystemPage";

export default function App() {
  const { toasts, dismissToast } = useToast();

  return (
    <>
      <Sidebar />
      <Routes>
        <Route path="/" element={<ScanPage />} />
        <Route path="/live" element={<LiveMonitorPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/evolution" element={<EvolutionPage />} />
        <Route path="/queue" element={<QueuePage />} />
        <Route path="/network" element={<NetworkPage />} />
        <Route path="/incidents" element={<IncidentsPage />} />
        <Route path="/system" element={<SystemPage />} />
        <Route path="/about" element={<AboutPage />} />
      </Routes>
      <Toast toasts={toasts} dismissToast={dismissToast} />
    </>
  );
}
