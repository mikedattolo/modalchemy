import { useState, useEffect } from "react";
import {
  FolderTree,
  File,
  Folder,
  RefreshCw,
  Download,
  ChevronRight,
  ChevronDown,
} from "lucide-react";

const BACKEND = "http://localhost:8420";

interface TreeNode {
  name: string;
  path: string;
  is_dir: boolean;
  children?: TreeNode[];
}

interface Workspace {
  id: string;
  jar_name: string;
  created_at: string;
}

export function WorkspacePage() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [tree, setTree] = useState<TreeNode | null>(null);
  const [fileContent, setFileContent] = useState<string>("");
  const [selectedFile, setSelectedFile] = useState<string>("");

  useEffect(() => {
    fetchWorkspaces();
  }, []);

  async function fetchWorkspaces() {
    try {
      const res = await fetch(`${BACKEND}/api/workspaces`);
      if (res.ok) setWorkspaces(await res.json());
    } catch {
      /* backend not running */
    }
  }

  async function loadTree(workspaceId: string) {
    setSelected(workspaceId);
    try {
      const res = await fetch(`${BACKEND}/api/workspaces/${encodeURIComponent(workspaceId)}/tree`);
      if (res.ok) setTree(await res.json());
    } catch {
      /* backend not running */
    }
  }

  async function loadFile(filePath: string) {
    if (!selected) return;
    setSelectedFile(filePath);
    try {
      const res = await fetch(
        `${BACKEND}/api/workspaces/${encodeURIComponent(selected)}/file?path=${encodeURIComponent(filePath)}`,
      );
      if (res.ok) setFileContent(await res.text());
    } catch {
      setFileContent("// Could not load file");
    }
  }

  return (
    <div className="flex h-full flex-col space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Workspace Browser</h1>
          <p className="mt-1 text-sm text-gray-400">
            Browse decompiled mod sources and resources.
          </p>
        </div>
        <button
          onClick={fetchWorkspaces}
          className="flex items-center gap-2 rounded-md bg-gray-800 px-3 py-1.5 text-sm text-gray-300 hover:bg-gray-700"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </button>
      </div>

      {/* Workspace selector */}
      {workspaces.length > 0 ? (
        <div className="flex gap-2 overflow-x-auto">
          {workspaces.map((ws) => (
            <button
              key={ws.id}
              onClick={() => loadTree(ws.id)}
              className={`flex-shrink-0 rounded-md px-3 py-1.5 text-sm ${
                selected === ws.id
                  ? "bg-forge-700/30 text-forge-300"
                  : "bg-gray-800 text-gray-400 hover:bg-gray-700"
              }`}
            >
              {ws.jar_name}
            </button>
          ))}
        </div>
      ) : (
        <div className="flex flex-1 flex-col items-center justify-center text-gray-500">
          <FolderTree className="mb-3 h-12 w-12" />
          <p className="text-sm">No workspaces yet — import a mod JAR first.</p>
        </div>
      )}

      {/* Tree + file view */}
      {tree && (
        <div className="flex flex-1 gap-4 overflow-hidden">
          {/* File tree */}
          <div className="workspace-tree w-72 flex-shrink-0 overflow-y-auto rounded-lg bg-gray-900 p-3">
            <TreeNodeView node={tree} onFileClick={loadFile} />
          </div>

          {/* File content */}
          <div className="flex-1 overflow-auto rounded-lg bg-gray-900 p-4">
            {selectedFile ? (
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-xs text-gray-500">{selectedFile}</span>
                  <button className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300">
                    <Download className="h-3 w-3" />
                    Export
                  </button>
                </div>
                <pre className="text-xs leading-relaxed text-gray-300">
                  <code>{fileContent}</code>
                </pre>
              </div>
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-gray-500">
                Select a file to view
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function TreeNodeView({
  node,
  onFileClick,
  depth = 0,
}: {
  node: TreeNode;
  onFileClick: (path: string) => void;
  depth?: number;
}) {
  const [open, setOpen] = useState(depth < 2);

  if (!node.is_dir) {
    return (
      <button
        onClick={() => onFileClick(node.path)}
        className="flex w-full items-center gap-1.5 rounded px-1 py-0.5 text-left text-xs text-gray-400 hover:bg-gray-800 hover:text-gray-200"
        style={{ paddingLeft: `${depth * 12 + 4}px` }}
      >
        <File className="h-3 w-3 flex-shrink-0" />
        <span className="truncate">{node.name}</span>
      </button>
    );
  }

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-1.5 rounded px-1 py-0.5 text-left text-xs font-medium text-gray-300 hover:bg-gray-800"
        style={{ paddingLeft: `${depth * 12 + 4}px` }}
      >
        {open ? (
          <ChevronDown className="h-3 w-3 flex-shrink-0" />
        ) : (
          <ChevronRight className="h-3 w-3 flex-shrink-0" />
        )}
        <Folder className="h-3 w-3 flex-shrink-0 text-forge-400" />
        <span className="truncate">{node.name}</span>
      </button>
      {open &&
        node.children?.map((child) => (
          <TreeNodeView
            key={child.path}
            node={child}
            onFileClick={onFileClick}
            depth={depth + 1}
          />
        ))}
    </div>
  );
}
