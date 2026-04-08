import { useState } from "react";
import { Image, Wand2, Shuffle, Loader2, Download } from "lucide-react";

const AI_BACKEND = "http://localhost:8421";

type Mode = "generate" | "remix";

interface GeneratedTexture {
  id: string;
  prompt: string;
  image_base64: string;
  size: number;
}

export function TextureGenPage() {
  const [mode, setMode] = useState<Mode>("generate");
  const [prompt, setPrompt] = useState("");
  const [size, setSize] = useState<16 | 32>(16);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<GeneratedTexture[]>([]);
  const [remixFile, setRemixFile] = useState<File | null>(null);

  async function handleGenerate() {
    if (!prompt.trim()) return;
    setLoading(true);

    try {
      const res = await fetch(`${AI_BACKEND}/api/textures/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, size, mode }),
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

  async function handleRemix() {
    if (!remixFile) return;
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append("image", remixFile);
      formData.append("prompt", prompt);
      formData.append("size", String(size));

      const res = await fetch(`${AI_BACKEND}/api/textures/remix`, {
        method: "POST",
        body: formData,
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">AI Texture Generation</h1>
        <p className="mt-1 text-sm text-gray-400">
          Generate Minecraft-style pixel art textures from text prompts, or remix
          existing textures.
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
            placeholder="e.g., cobblestone block texture, mossy, dark fantasy style"
            rows={3}
            className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:border-forge-500 focus:outline-none"
          />
        </div>

        <div className="flex gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-300">
              Size
            </label>
            <div className="flex gap-2">
              {([16, 32] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => setSize(s)}
                  className={`rounded-md px-3 py-1.5 text-sm ${
                    size === s
                      ? "bg-forge-600 text-white"
                      : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                  }`}
                >
                  {s}×{s}
                </button>
              ))}
            </div>
          </div>
        </div>

        {mode === "remix" && (
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-300">
              Source Texture
            </label>
            <input
              type="file"
              accept="image/png"
              onChange={(e) => setRemixFile(e.target.files?.[0] ?? null)}
              className="text-sm text-gray-400 file:mr-3 file:rounded-md file:border-0 file:bg-gray-800 file:px-3 file:py-1.5 file:text-sm file:text-gray-300 hover:file:bg-gray-700"
            />
          </div>
        )}

        <button
          onClick={mode === "generate" ? handleGenerate : handleRemix}
          disabled={loading || !prompt.trim()}
          className="flex items-center gap-2 rounded-md bg-forge-600 px-5 py-2 text-sm font-medium text-white hover:bg-forge-500 disabled:opacity-50"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Wand2 className="h-4 w-4" />
          )}
          {mode === "generate" ? "Generate" : "Remix"}
        </button>
      </div>

      {/* Results grid */}
      {results.length > 0 && (
        <div>
          <h2 className="mb-3 text-lg font-semibold text-white">Results</h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
            {results.map((tex) => (
              <div
                key={tex.id}
                className="group relative overflow-hidden rounded-lg bg-gray-900"
              >
                <div className="aspect-square p-2">
                  <img
                    src={`data:image/png;base64,${tex.image_base64}`}
                    alt={tex.prompt}
                    className="h-full w-full object-contain"
                    style={{ imageRendering: "pixelated" }}
                  />
                </div>
                <div className="absolute inset-0 flex items-end bg-gradient-to-t from-black/70 to-transparent opacity-0 transition-opacity group-hover:opacity-100">
                  <div className="flex w-full items-center justify-between p-2">
                    <span className="truncate text-xs text-gray-300">
                      {tex.prompt}
                    </span>
                    <button className="text-gray-300 hover:text-white">
                      <Download className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {results.length === 0 && (
        <div className="flex flex-col items-center py-12 text-gray-500">
          <Image className="mb-3 h-12 w-12" />
          <p className="text-sm">
            Generated textures will appear here. Make sure the AI inference
            server is running on port 8421.
          </p>
        </div>
      )}
    </div>
  );
}
