import { useState } from "react";
import { Box, Wand2, Shuffle, Loader2, Copy, Check } from "lucide-react";

const AI_BACKEND = "http://localhost:8421";

type Mode = "generate" | "remix";

interface GeneratedModel {
  id: string;
  prompt: string;
  model_json: string;
  model_type: string;
}

export function ModelGenPage() {
  const [mode, setMode] = useState<Mode>("generate");
  const [prompt, setPrompt] = useState("");
  const [modelType, setModelType] = useState<"block" | "item">("block");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<GeneratedModel[]>([]);
  const [copied, setCopied] = useState<string | null>(null);

  async function handleGenerate() {
    if (!prompt.trim()) return;
    setLoading(true);

    try {
      const res = await fetch(`${AI_BACKEND}/api/models/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, model_type: modelType, mode }),
      });

      if (res.ok) {
        const data = await res.json();
        setResults((prev) => [data, ...prev]);
      }
    } catch {
      /* inference server not running */
    } finally {
      setLoading(false);
    }
  }

  async function handleCopy(id: string, json: string) {
    await navigator.clipboard.writeText(json);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">AI Model Generation</h1>
        <p className="mt-1 text-sm text-gray-400">
          Generate Minecraft block/item JSON models from text prompts.
        </p>
      </div>

      {/* Mode toggle */}
      <div className="flex gap-2">
        <button
          onClick={() => setMode("generate")}
          className={`flex items-center gap-2 rounded-md px-4 py-2 text-sm ${
            mode === "generate"
              ? "bg-forge-700/30 text-forge-300"
              : "bg-gray-800 text-gray-400 hover:bg-gray-700"
          }`}
        >
          <Wand2 className="h-4 w-4" />
          Generate
        </button>
        <button
          onClick={() => setMode("remix")}
          className={`flex items-center gap-2 rounded-md px-4 py-2 text-sm ${
            mode === "remix"
              ? "bg-forge-700/30 text-forge-300"
              : "bg-gray-800 text-gray-400 hover:bg-gray-700"
          }`}
        >
          <Shuffle className="h-4 w-4" />
          Remix
        </button>
      </div>

      {/* Controls */}
      <div className="space-y-4 rounded-lg bg-gray-900 p-5">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-300">
            Prompt
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g., a wooden barrel block with iron bands, 3D with rotation"
            rows={3}
            className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:border-forge-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-300">
            Model Type
          </label>
          <div className="flex gap-2">
            {(["block", "item"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setModelType(t)}
                className={`rounded-md px-3 py-1.5 text-sm capitalize ${
                  modelType === t
                    ? "bg-forge-600 text-white"
                    : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {mode === "remix" && (
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-300">
              Source Model JSON
            </label>
            <textarea
              placeholder="Paste an existing model JSON to remix…"
              rows={5}
              className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-2 font-mono text-xs text-gray-200 placeholder-gray-500 focus:border-forge-500 focus:outline-none"
            />
          </div>
        )}

        <button
          onClick={handleGenerate}
          disabled={loading || !prompt.trim()}
          className="flex items-center gap-2 rounded-md bg-forge-600 px-5 py-2 text-sm font-medium text-white hover:bg-forge-500 disabled:opacity-50"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Wand2 className="h-4 w-4" />
          )}
          {mode === "generate" ? "Generate Model" : "Remix Model"}
        </button>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-white">Results</h2>
          {results.map((model) => (
            <div key={model.id} className="rounded-lg bg-gray-900 p-4">
              <div className="mb-2 flex items-center justify-between">
                <div>
                  <span className="text-sm font-medium text-gray-200">
                    {model.prompt}
                  </span>
                  <span className="ml-2 rounded bg-gray-800 px-2 py-0.5 text-xs text-gray-400">
                    {model.model_type}
                  </span>
                </div>
                <button
                  onClick={() => handleCopy(model.id, model.model_json)}
                  className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-200"
                >
                  {copied === model.id ? (
                    <Check className="h-3.5 w-3.5 text-green-400" />
                  ) : (
                    <Copy className="h-3.5 w-3.5" />
                  )}
                  Copy JSON
                </button>
              </div>
              <pre className="max-h-64 overflow-auto rounded bg-gray-950 p-3 text-xs text-gray-300">
                {model.model_json}
              </pre>
            </div>
          ))}
        </div>
      )}

      {results.length === 0 && (
        <div className="flex flex-col items-center py-12 text-gray-500">
          <Box className="mb-3 h-12 w-12" />
          <p className="text-sm">
            Generated models will appear here. Make sure the AI inference server
            is running on port 8421.
          </p>
        </div>
      )}
    </div>
  );
}
