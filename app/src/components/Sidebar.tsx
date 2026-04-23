import { NavLink } from "react-router-dom";
import {
  PackagePlus,
  FolderTree,
  Image,
  Box,
  Library,
  Sparkles,
  Settings,
  Hammer,
} from "lucide-react";

const links = [
  { to: "/import", label: "Import", icon: PackagePlus },
  { to: "/workspace", label: "Workspace", icon: FolderTree },
  { to: "/textures", label: "Textures", icon: Image },
  { to: "/models", label: "Models", icon: Box },
  { to: "/library", label: "Library", icon: Library },
  { to: "/ai-studio", label: "AI Studio", icon: Sparkles },
  { to: "/settings", label: "Settings", icon: Settings },
] as const;

export function Sidebar() {
  return (
    <aside className="flex w-56 flex-col border-r border-gray-800 bg-gray-900">
      {/* Brand */}
      <div className="flex items-center gap-2 border-b border-gray-800 px-4 py-4">
        <Hammer className="h-6 w-6 text-forge-400" />
        <span className="text-lg font-bold tracking-tight text-white">
          ModForge
        </span>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-1 px-2 py-3">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-forge-700/30 text-forge-300"
                  : "text-gray-400 hover:bg-gray-800 hover:text-gray-200"
              }`
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-gray-800 px-4 py-3 text-xs text-gray-500">
        ModForge v0.1.0
      </div>
    </aside>
  );
}
