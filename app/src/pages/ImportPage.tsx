import { useState } from "react";
import { Upload, FileArchive, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";

const BACKEND = "http://localhost:8420";

type DecompileStatus = "idle" | "uploading" | "decompiling" | "done" | "error";

interface DecompileReport {
  workspace_id: string;
  jar_name: string;
  mod_loader: string;
  source_files: number;
  resource_files: number;
  errors: string[];
}

export function ImportPage() {
  const [status, setStatus] = useState<DecompileStatus>("idle");
  const [report, setReport] = useState<DecompileReport | null>(null);
  const [error, setError] = useState<string>("");
  const [dragOver, setDragOver] = useState(false);

  async function handleFile(file: File) {
    if (!file.name.endsWith(".jar")) {
      setError("Please select a .jar file");
      setStatus("error");
      return;
    }

    setStatus("uploading");
    setError("");
    setReport(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      setStatus("decompiling");
      const res = await fetch(`${BACKEND}/api/decompile`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(body.detail || "Decompilation failed");
      }

      const data: DecompileReport = await res.json();
      setReport(data);
      setStatus("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setStatus("error");
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function handleFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Import & Decompile</h1>
        <p className="mt-1 text-sm text-gray-400">
          Select a Minecraft Forge mod JAR (1.6.4 or 1.7.10) to decompile and
          extract into a workspace.
        </p>
      </div>

      {/* Drop zone */}
      <label
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-12 transition-colors ${
          dragOver
            ? "border-forge-400 bg-forge-900/20"
            : "border-gray-700 hover:border-gray-500"
        }`}
      >
        <Upload className="mb-3 h-10 w-10 text-gray-500" />
        <span className="text-sm font-medium text-gray-300">
          Drop a .jar file here or click to browse
        </span>
        <span className="mt-1 text-xs text-gray-500">
          Supports Forge mods for Minecraft 1.6.4 and 1.7.10
        </span>
        <input
          type="file"
          accept=".jar"
          className="hidden"
          onChange={handleFileInput}
        />
      </label>

      {/* Status */}
      {status === "decompiling" && (
        <div className="flex items-center gap-3 rounded-lg bg-gray-800 p-4">
          <Loader2 className="h-5 w-5 animate-spin text-forge-400" />
          <span className="text-sm text-gray-300">
            Decompiling… this may take a moment.
          </span>
        </div>
      )}

      {status === "error" && (
        <div className="flex items-center gap-3 rounded-lg bg-red-900/30 p-4">
          <AlertCircle className="h-5 w-5 text-red-400" />
          <span className="text-sm text-red-300">{error}</span>
        </div>
      )}

      {status === "done" && report && (
        <div className="space-y-3 rounded-lg bg-gray-800 p-5">
          <div className="flex items-center gap-2 text-green-400">
            <CheckCircle2 className="h-5 w-5" />
            <span className="font-medium">Decompilation complete</span>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <Stat icon={FileArchive} label="JAR" value={report.jar_name} />
            <Stat icon={FileArchive} label="Mod Loader" value={report.mod_loader} />
            <Stat icon={FileArchive} label="Source Files" value={String(report.source_files)} />
            <Stat icon={FileArchive} label="Resources" value={String(report.resource_files)} />
          </div>
          {report.errors.length > 0 && (
            <div className="mt-2 text-xs text-yellow-400">
              {report.errors.length} file(s) had decompilation warnings — see
              report for details.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
}: {
  icon: React.ComponentType;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-md bg-gray-900 px-3 py-2">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="truncate font-medium text-gray-200">{value}</div>
    </div>
  );
}
