import { useEffect, useMemo, useState } from "react";
import {
  Sparkles,
  SlidersHorizontal,
  RefreshCw,
  Loader2,
  Copy,
  Check,
  Image as ImageIcon,
} from "lucide-react";

const AI_BACKEND = "http://localhost:8421";

type ModelType = "block" | "item";

interface ConfigOptions {
  texture_checkpoints: string[];
  model_datasets: string[];
  active_texture_checkpoint: string | null;
  active_model_dataset: string | null;
}

interface AssetBundle {
  id: string;
  prompt: string;
  texture: {
    id: string;
    prompt: string;
    image_base64: string;
    size: number;
    texture_name: string;
  };
  model: {
    id: string;
    prompt: string;
    model_json: string;
    model_type: string;
  };
}

export function AIStudioPage() {
  const [prompt, setPrompt] = useState("");
  const [texturePrompt, setTexturePrompt] = useState("");
  const [size, setSize] = useState<16 | 32>(16);
  const [modelType, setModelType] = useState<ModelType>("block");

  const [options, setOptions] = useState<ConfigOptions | null>(null);
  const [selectedTextureCheckpoint, setSelectedTextureCheckpoint] = useState("");
  const [selectedModelDataset, setSelectedModelDataset] = useState("");

  const [loadingOptions, setLoadingOptions] = useState(false);
  const [applyingConfig, setApplyingConfig] = useState(false);
  const [generating, setGenerating] = useState(false);

  const [bundle, setBundle] = useState<AssetBundle | null>(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  const texturePreviewSrc = useMemo(() => {
    if (!bundle) return "";
    return `data:image/png;base64,${bundle.texture.image_base64}`;
  }, [bundle]);

  useEffect(() => {
    void loadOptions();
  }, []);

  async function loadOptions() {
    setLoadingOptions(true);
    setError("");
    try {
      const res = await fetch(`${AI_BACKEND}/api/config/options`);
      if (!res.ok) throw new Error("Could not load AI runtime options");
      const data: ConfigOptions = await res.json();
      setOptions(data);
      setSelectedTextureCheckpoint(data.active_texture_checkpoint ?? data.texture_checkpoints[0] ?? "");
      setSelectedModelDataset(data.active_model_dataset ?? data.model_datasets[0] ?? "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI server is not reachable");
    } finally {
      setLoadingOptions(false);
    }
  }

  async function applyConfig() {
    setApplyingConfig(true);
    setError("");
    try {
      const res = await fetch(`${AI_BACKEND}/api/config/active`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          texture_checkpoint: selectedTextureCheckpoint || null,
          model_dataset: selectedModelDataset || null,
        }),
      });
      if (!res.ok) throw new Error("Failed to apply active models");
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "Failed to apply active models");
      await loadOptions();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to apply configuration");
    } finally {
      setApplyingConfig(false);
    }
  }

  async function generateLinked() {
    if (!prompt.trim()) return;

    setGenerating(true);
    setError("");
    try {
      const res = await fetch(`${AI_BACKEND}/api/assets/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt,
          texture_prompt: texturePrompt.trim() || undefined,
          size,
          model_type: modelType,
        }),
      });
      if (!res.ok) throw new Error("Linked generation failed");
      const data: AssetBundle = await res.json();
      setBundle(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  }

  async function copyModelJson() {
    if (!bundle) return;
    await navigator.clipboard.writeText(bundle.model.model_json);
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  }

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
      <section className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 p-6 shadow-2xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-3xl font-black tracking-tight text-slate-100">AI Studio</h1>
            <p className="mt-1 text-sm text-slate-300">
              Generate matched texture + model pairs, then switch checkpoints and compare quality.
            </p>
          </div>
          <button
            onClick={loadOptions}
            disabled={loadingOptions}
            className="inline-flex items-center gap-2 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800 disabled:opacity-60"
          >
            {loadingOptions ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            Refresh Models
          </button>
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <Card title="Texture Checkpoint">
            <select
              value={selectedTextureCheckpoint}
              onChange={(e) => setSelectedTextureCheckpoint(e.target.value)}
              className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200"
            >
              <option value="">Auto (latest discovered)</option>
              {(options?.texture_checkpoints ?? []).map((ckpt) => (
                <option key={ckpt} value={ckpt}>
                  {basename(ckpt)}
                </option>
              ))}
            </select>
            <p className="mt-2 text-xs text-slate-400 break-all">
              Active: {options?.active_texture_checkpoint ?? "placeholder"}
            </p>
          </Card>

          <Card title="Model Dataset">
            <select
              value={selectedModelDataset}
              onChange={(e) => setSelectedModelDataset(e.target.value)}
              className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200"
            >
              <option value="">Default fallback dataset</option>
              {(options?.model_datasets ?? []).map((dataset) => (
                <option key={dataset} value={dataset}>
                  {basename(dataset)}
                </option>
              ))}
            </select>
            <p className="mt-2 text-xs text-slate-400 break-all">
              Active: {options?.active_model_dataset ?? "generator fallback"}
            </p>
          </Card>
        </div>

        <div className="mt-4">
          <button
            onClick={applyConfig}
            disabled={applyingConfig}
            className="inline-flex items-center gap-2 rounded-md bg-forge-600 px-4 py-2 text-sm font-semibold text-white hover:bg-forge-500 disabled:opacity-60"
          >
            {applyingConfig ? <Loader2 className="h-4 w-4 animate-spin" /> : <SlidersHorizontal className="h-4 w-4" />}
            Apply Active Models
          </button>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
          <h2 className="text-lg font-bold text-slate-100">Linked Generation</h2>
          <p className="mt-1 text-sm text-slate-400">
            One request generates both assets and binds model texture paths to the generated texture name.
          </p>

          <div className="mt-4 space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-300">Concept Prompt</label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="e.g. giraffe statue block, stylized safari stone"
                rows={3}
                className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-300">Texture Prompt (optional)</label>
              <input
                value={texturePrompt}
                onChange={(e) => setTexturePrompt(e.target.value)}
                placeholder="Use this if texture style should differ from model prompt"
                className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
              />
            </div>

            <div className="flex flex-wrap gap-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-300">Model Type</label>
                <div className="flex gap-2">
                  {(["block", "item"] as const).map((t) => (
                    <button
                      key={t}
                      onClick={() => setModelType(t)}
                      className={`rounded-md px-3 py-1.5 text-sm capitalize ${
                        modelType === t
                          ? "bg-forge-600 text-white"
                          : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                      }`}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-300">Texture Size</label>
                <div className="flex gap-2">
                  {([16, 32] as const).map((s) => (
                    <button
                      key={s}
                      onClick={() => setSize(s)}
                      className={`rounded-md px-3 py-1.5 text-sm ${
                        size === s
                          ? "bg-forge-600 text-white"
                          : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                      }`}
                    >
                      {s}x{s}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <button
              onClick={generateLinked}
              disabled={generating || !prompt.trim()}
              className="inline-flex items-center gap-2 rounded-md bg-emerald-600 px-5 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-60"
            >
              {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              Generate Matched Assets
            </button>

            {error && <p className="rounded-md bg-red-950/60 p-2 text-sm text-red-300">{error}</p>}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
          <h2 className="text-lg font-bold text-slate-100">Result Preview</h2>
          {!bundle ? (
            <div className="mt-8 flex flex-col items-center text-slate-500">
              <ImageIcon className="mb-3 h-10 w-10" />
              <p className="text-sm">No result yet. Generate a linked pair to preview.</p>
            </div>
          ) : (
            <div className="mt-4 space-y-4">
              <div className="rounded-xl border border-slate-700 bg-slate-950 p-3">
                <div className="mb-2 text-xs text-slate-400">Texture ({bundle.texture.texture_name})</div>
                <img
                  src={texturePreviewSrc}
                  alt={bundle.texture.prompt}
                  className="h-48 w-48 rounded border border-slate-800 object-contain"
                  style={{ imageRendering: "pixelated" }}
                />
              </div>

              <div className="rounded-xl border border-slate-700 bg-slate-950 p-3">
                <div className="mb-2 flex items-center justify-between">
                  <div className="text-xs text-slate-400">Model JSON</div>
                  <button
                    onClick={copyModelJson}
                    className="inline-flex items-center gap-1 text-xs text-slate-300 hover:text-white"
                  >
                    {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                    Copy
                  </button>
                </div>
                <pre className="max-h-64 overflow-auto text-xs text-slate-300">
                  {bundle.model.model_json}
                </pre>
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
      <h3 className="mb-2 text-sm font-semibold text-slate-200">{title}</h3>
      {children}
    </div>
  );
}

function basename(path: string): string {
  const split = path.split("/");
  return split[split.length - 1] || path;
}
