import { useState, useEffect } from "react";
import { Settings, Save, CheckCircle2 } from "lucide-react";

const BACKEND = "http://localhost:8420";

interface AppSettings {
  backend_port: number;
  ai_port: number;
  workspace_dir: string;
  decompiler: string;
  java_path: string;
  theme: string;
  auto_decompile: boolean;
}

const DEFAULT_SETTINGS: AppSettings = {
  backend_port: 8420,
  ai_port: 8421,
  workspace_dir: "./workspaces",
  decompiler: "cfr",
  java_path: "java",
  theme: "dark",
  auto_decompile: true,
};

export function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  async function fetchSettings() {
    try {
      const res = await fetch(`${BACKEND}/api/settings`);
      if (res.ok) setSettings(await res.json());
    } catch {
      /* use defaults */
    }
  }

  async function handleSave() {
    try {
      await fetch(`${BACKEND}/api/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      /* backend not running */
    }
  }

  function update<K extends keyof AppSettings>(key: K, value: AppSettings[K]) {
    setSettings((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="mt-1 text-sm text-gray-400">
          Configure ModForge behaviour, paths, and preferences.
        </p>
      </div>

      <div className="space-y-6 rounded-lg bg-gray-900 p-6">
        {/* Backend */}
        <Section title="Backend Service">
          <Field label="Backend Port">
            <input
              type="number"
              value={settings.backend_port}
              onChange={(e) => update("backend_port", Number(e.target.value))}
              className="input-field"
            />
          </Field>
          <Field label="AI Inference Port">
            <input
              type="number"
              value={settings.ai_port}
              onChange={(e) => update("ai_port", Number(e.target.value))}
              className="input-field"
            />
          </Field>
        </Section>

        {/* Decompiler */}
        <Section title="Decompiler">
          <Field label="Decompiler Engine">
            <select
              value={settings.decompiler}
              onChange={(e) => update("decompiler", e.target.value)}
              className="input-field"
            >
              <option value="cfr">CFR (default)</option>
              <option value="fernflower">FernFlower</option>
              <option value="procyon">Procyon</option>
            </select>
          </Field>
          <Field label="Java Path">
            <input
              type="text"
              value={settings.java_path}
              onChange={(e) => update("java_path", e.target.value)}
              className="input-field"
            />
          </Field>
          <Field label="Auto-decompile on Import">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={settings.auto_decompile}
                onChange={(e) => update("auto_decompile", e.target.checked)}
                className="rounded border-gray-600 bg-gray-800 text-forge-500"
              />
              <span className="text-sm text-gray-300">
                Automatically decompile after extraction
              </span>
            </label>
          </Field>
        </Section>

        {/* Workspace */}
        <Section title="Workspace">
          <Field label="Workspace Directory">
            <input
              type="text"
              value={settings.workspace_dir}
              onChange={(e) => update("workspace_dir", e.target.value)}
              className="input-field"
            />
          </Field>
        </Section>

        {/* Save */}
        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={handleSave}
            className="flex items-center gap-2 rounded-md bg-forge-600 px-5 py-2 text-sm font-medium text-white hover:bg-forge-500"
          >
            <Save className="h-4 w-4" />
            Save Settings
          </button>
          {saved && (
            <span className="flex items-center gap-1 text-sm text-green-400">
              <CheckCircle2 className="h-4 w-4" />
              Saved
            </span>
          )}
        </div>
      </div>

      {/* System info */}
      <div className="rounded-lg bg-gray-900 p-6">
        <h2 className="mb-3 text-sm font-semibold text-gray-300">
          System Info
        </h2>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <InfoRow label="App Version" value="0.1.0" />
          <InfoRow label="Backend" value={`localhost:${settings.backend_port}`} />
          <InfoRow label="AI Server" value={`localhost:${settings.ai_port}`} />
          <InfoRow label="Decompiler" value={settings.decompiler.toUpperCase()} />
        </div>
      </div>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-300">
        <Settings className="h-4 w-4" />
        {title}
      </h2>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between">
      <label className="text-sm text-gray-400">{label}</label>
      <div className="w-48">{children}</div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <>
      <span className="text-gray-500">{label}</span>
      <span className="text-gray-300">{value}</span>
    </>
  );
}
