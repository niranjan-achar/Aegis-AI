import { Route, Routes } from "react-router-dom";

import Sidebar from "./components/layout/Sidebar";
import Toast from "./components/layout/Toast";
import { useToast } from "./hooks/useToast.jsx";
import AboutPage from "./pages/AboutPage";
import EvolutionPage from "./pages/EvolutionPage";
import QueuePage from "./pages/QueuePage";
import ScanPage from "./pages/ScanPage";

export default function App() {
  const { toasts, dismissToast } = useToast();

  return (
    <>
      <Sidebar />
      <Routes>
        <Route path="/" element={<ScanPage />} />
        <Route path="/evolution" element={<EvolutionPage />} />
        <Route path="/queue" element={<QueuePage />} />
        <Route path="/about" element={<AboutPage />} />
      </Routes>
      <Toast toasts={toasts} dismissToast={dismissToast} />
    </>
  );
}
