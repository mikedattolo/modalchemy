import { useCallback, useEffect, useState } from "react";
import { DownloadCloud, Search, Loader2, CheckCircle2 } from "lucide-react";

const BACKEND = "http://localhost:8420";

type McVersion = "1.6.4" | "1.7.10";

interface LibraryItem {
  project_id: string;
  slug: string;
  title: string;
  description: string;
  downloads: number;
  author: string;
  icon_url?: string | null;
}

interface CatalogResponse {
  source: string;
  minecraft_version: McVersion;
  count: number;
  results: LibraryItem[];
}

export function LibraryPage() {
  const [query, setQuery] = useState("");
  const [version, setVersion] = useState<McVersion>("1.7.10");
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [error, setError] = useState("");
  const [importingProjectId, setImportingProjectId] = useState<string | null>(null);
  const [lastImported, setLastImported] = useState<string>("");

  const searchCatalog = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({
        query: query.trim(),
        minecraft_version: version,
        limit: "24",
      });
      const res = await fetch(`${BACKEND}/api/library/catalog?${params.toString()}`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(body.detail || "Failed to search catalog");
      }

      const data: CatalogResponse = await res.json();
      setItems(data.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to search catalog");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [query, version]);

  useEffect(() => {
    void searchCatalog();
  }, [searchCatalog]);

  async function importAndDecompile(item: LibraryItem) {
    setImportingProjectId(item.project_id);
    setError("");
    setLastImported("");

    try {
      const res = await fetch(`${BACKEND}/api/library/import`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: item.project_id,
          minecraft_version: version,
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(body.detail || "Import failed");
      }

      const data = await res.json();
      const ws = data.report?.workspace_id as string | undefined;
      if (ws) setLastImported(`${item.title} -> ${ws}`);
      else setLastImported(`${item.title} imported`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setImportingProjectId(null);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Mod Library</h1>
        <p className="mt-1 text-sm text-gray-400">
          Browse Forge mods by version and one-click download + auto-decompile into your workspace.
        </p>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-64 flex-1">
            <label className="mb-1 block text-sm text-slate-300">Search</label>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void searchCatalog();
              }}
              placeholder="e.g. thaumcraft, buildcraft, industrial"
              className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm text-slate-300">Minecraft Version</label>
            <div className="flex gap-2">
              {(["1.6.4", "1.7.10"] as const).map((v) => (
                <button
                  key={v}
                  onClick={() => setVersion(v)}
                  className={`rounded-md px-3 py-2 text-sm ${
                    version === v
                      ? "bg-forge-600 text-white"
                      : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                  }`}
                >
                  {v}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={() => void searchCatalog()}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-60"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            Search
          </button>
        </div>

        {error && <p className="mt-3 text-sm text-red-300">{error}</p>}
        {lastImported && (
          <p className="mt-3 inline-flex items-center gap-1 text-sm text-emerald-300">
            <CheckCircle2 className="h-4 w-4" />
            {lastImported}
          </p>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {items.map((item) => (
          <div key={item.project_id} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <div className="flex items-start gap-3">
              <img
                src={item.icon_url || "https://placehold.co/64x64/0f172a/e2e8f0?text=MOD"}
                alt={item.title}
                className="h-12 w-12 rounded-md border border-slate-700 object-cover"
              />
              <div className="min-w-0 flex-1">
                <h3 className="truncate text-sm font-semibold text-slate-100">{item.title}</h3>
                <p className="text-xs text-slate-400">by {item.author || "unknown"}</p>
                <p className="mt-1 text-xs text-slate-500">{item.downloads.toLocaleString()} downloads</p>
              </div>
            </div>

            <p className="mt-3 line-clamp-3 text-xs text-slate-300">{item.description || "No description."}</p>

            <button
              onClick={() => void importAndDecompile(item)}
              disabled={importingProjectId === item.project_id}
              className="mt-4 inline-flex items-center gap-2 rounded-md bg-forge-600 px-3 py-2 text-sm text-white hover:bg-forge-500 disabled:opacity-60"
            >
              {importingProjectId === item.project_id ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <DownloadCloud className="h-4 w-4" />
              )}
              Download + Decompile
            </button>
          </div>
        ))}
      </div>

      {!loading && items.length === 0 && !error && (
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-6 text-sm text-slate-400">
          No mods found yet. Try a different query or version.
        </div>
      )}
    </div>
  );
}
