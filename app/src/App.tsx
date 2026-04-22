import { Routes, Route, Navigate } from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { ImportPage } from "./pages/ImportPage";
import { WorkspacePage } from "./pages/WorkspacePage";
import { TextureGenPage } from "./pages/TextureGenPage";
import { ModelGenPage } from "./pages/ModelGenPage";
import { SettingsPage } from "./pages/SettingsPage";
import { AIStudioPage } from "./pages/AIStudioPage";

function App() {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-950 text-slate-100">
      <Sidebar />
      <main className="flex-1 overflow-auto p-6">
        <Routes>
          <Route path="/" element={<Navigate to="/import" replace />} />
          <Route path="/import" element={<ImportPage />} />
          <Route path="/workspace" element={<WorkspacePage />} />
          <Route path="/textures" element={<TextureGenPage />} />
          <Route path="/models" element={<ModelGenPage />} />
          <Route path="/ai-studio" element={<AIStudioPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
