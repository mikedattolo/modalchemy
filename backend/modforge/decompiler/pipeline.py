"""End-to-end decompile / extract pipeline.

Steps:
  1. Validate the JAR (is it a real ZIP? does it contain class files?)
  2. Detect Forge version (1.6.4 vs 1.7.10) via mcmod.info / @Mod annotation
  3. Extract all resources into a workspace folder
  4. Run the selected Java decompiler on .class files
  5. Produce a JSON report
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from modforge.decompiler.validator import validate_jar, JarInfo

logger = logging.getLogger(__name__)


class DecompileReport(BaseModel):
    workspace_id: str
    jar_name: str
    mod_loader: str
    minecraft_version: str
    source_files: int
    resource_files: int
    errors: list[str]
    created_at: str


class DecompilePipeline:
    """Orchestrates JAR validation → extraction → decompilation → report."""

    def __init__(
        self,
        jar_path: Path,
        jar_name: str,
        workspace_root: Path,
        decompiler: str = "cfr",
        java_path: str = "java",
        tools_dir: Path = Path("./tools"),
    ):
        self.jar_path = jar_path
        self.jar_name = jar_name
        self.workspace_root = workspace_root
        self.decompiler = decompiler
        self.java_path = java_path
        self.tools_dir = tools_dir

        self.workspace_id = f"{Path(jar_name).stem}_{uuid.uuid4().hex[:8]}"
        self.workspace_dir = workspace_root / self.workspace_id
        self.errors: list[str] = []

    def run(self) -> DecompileReport:
        """Execute the full pipeline and return a report."""
        # 1. Validate
        jar_info = validate_jar(self.jar_path)

        # 2. Create workspace structure
        self._create_workspace()

        # 3. Extract
        resource_count = self._extract()

        # 4. Decompile
        source_count = self._decompile()

        # 5. Build report
        report = DecompileReport(
            workspace_id=self.workspace_id,
            jar_name=self.jar_name,
            mod_loader=jar_info.mod_loader,
            minecraft_version=jar_info.minecraft_version,
            source_files=source_count,
            resource_files=resource_count,
            errors=self.errors,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Save report to workspace
        report_path = self.workspace_dir / "report.json"
        report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

        logger.info(
            "Decompile complete: %s → %s (%d sources, %d resources, %d errors)",
            self.jar_name,
            self.workspace_id,
            source_count,
            resource_count,
            len(self.errors),
        )
        return report

    def _create_workspace(self) -> None:
        """Create the workspace directory structure."""
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        (self.workspace_dir / "sources").mkdir(exist_ok=True)
        (self.workspace_dir / "resources").mkdir(exist_ok=True)
        (self.workspace_dir / "classes").mkdir(exist_ok=True)
        (self.workspace_dir / "logs").mkdir(exist_ok=True)

    def _extract(self) -> int:
        """Extract JAR contents into the workspace."""
        resource_count = 0
        classes_dir = self.workspace_dir / "classes"
        resources_dir = self.workspace_dir / "resources"

        with zipfile.ZipFile(self.jar_path, "r") as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue

                name = info.filename

                # Skip META-INF signatures (but keep manifest)
                if name.startswith("META-INF/") and name.endswith((".SF", ".RSA", ".DSA")):
                    continue

                if name.endswith(".class"):
                    target = classes_dir / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(zf.read(name))
                else:
                    target = resources_dir / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(zf.read(name))
                    resource_count += 1

        return resource_count

    def _decompile(self) -> int:
        """Run the Java decompiler on extracted .class files."""
        classes_dir = self.workspace_dir / "classes"
        sources_dir = self.workspace_dir / "sources"
        log_file = self.workspace_dir / "logs" / "decompile.log"

        class_files = list(classes_dir.rglob("*.class"))
        if not class_files:
            self.errors.append("No .class files found in JAR")
            return 0

        if self.decompiler == "cfr":
            return self._run_cfr(classes_dir, sources_dir, log_file)
        else:
            self.errors.append(f"Decompiler '{self.decompiler}' not yet implemented")
            return 0

    def _run_cfr(self, classes_dir: Path, sources_dir: Path, log_file: Path) -> int:
        """Run CFR decompiler."""
        cfr_jar = self.tools_dir / "cfr" / "cfr.jar"
        if not cfr_jar.exists():
            # Try alternative name
            cfr_jar = self.tools_dir / "cfr" / "cfr-0.152.jar"

        if not cfr_jar.exists():
            self.errors.append(
                f"CFR jar not found at {cfr_jar}. Run scripts/download-tools.py first."
            )
            # Still count sources as 0 — decompiler missing
            return 0

        cmd = [
            self.java_path,
            "-jar",
            str(cfr_jar),
            str(classes_dir),
            "--outputdir",
            str(sources_dir),
            "--silent",
            "false",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            log_file.write_text(
                f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}",
                encoding="utf-8",
            )

            if result.returncode != 0:
                self.errors.append(f"CFR exited with code {result.returncode}")
        except FileNotFoundError:
            self.errors.append(f"Java not found at '{self.java_path}'")
            return 0
        except subprocess.TimeoutExpired:
            self.errors.append("Decompilation timed out after 300 seconds")
            return 0

        # Count produced .java files
        source_files = list(sources_dir.rglob("*.java"))
        return len(source_files)
