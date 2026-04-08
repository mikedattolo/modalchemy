# Decompiler Plugins Guide

ModForge uses a pluggable decompiler architecture. The default is **CFR**, but
you can add support for FernFlower, Procyon, or any other Java decompiler.

---

## How It Works

The decompiler backend is invoked by `DecompilePipeline._decompile()` in
`backend/modforge/decompiler/pipeline.py`. Currently this calls `_run_cfr()`,
which shells out to the CFR JAR.

The flow is:

```
JAR → extract .class files → run decompiler → .java output → workspace
```

The decompiler receives:
- A directory of `.class` files (`workspace/classes/`)
- An output directory for `.java` sources (`workspace/sources/`)

---

## Adding a New Decompiler

### Step 1: Download the decompiler

Add the decompiler binary or JAR to the tools directory. Update
`scripts/download-tools.py`:

```python
TOOLS = {
    "cfr": {
        "url": "https://github.com/leibnitz27/cfr/releases/download/0.152/cfr-0.152.jar",
        "dest": "cfr/cfr.jar",
    },
    "fernflower": {
        "url": "https://example.com/fernflower.jar",
        "dest": "fernflower/fernflower.jar",
    },
}
```

### Step 2: Create the runner method

Add a `_run_fernflower()` method to `DecompilePipeline` in
`backend/modforge/decompiler/pipeline.py`:

```python
def _run_fernflower(self) -> int:
    """Run FernFlower decompiler."""
    fernflower_jar = self.tools_dir / "fernflower" / "fernflower.jar"
    if not fernflower_jar.exists():
        raise FileNotFoundError(
            f"FernFlower not found at {fernflower_jar}. "
            "Run: python scripts/download-tools.py"
        )

    classes_dir = self.workspace_dir / "classes"
    sources_dir = self.workspace_dir / "sources"

    cmd = [
        self.java_path,
        "-jar",
        str(fernflower_jar),
        str(classes_dir),
        str(sources_dir),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )

    if result.returncode != 0:
        self.errors.append(f"FernFlower error: {result.stderr[:500]}")

    return len(list(sources_dir.rglob("*.java")))
```

### Step 3: Wire it into the dispatcher

Update `_decompile()` in the same file:

```python
def _decompile(self) -> int:
    if self.decompiler == "cfr":
        return self._run_cfr()
    elif self.decompiler == "fernflower":
        return self._run_fernflower()
    elif self.decompiler == "procyon":
        return self._run_procyon()
    else:
        raise ValueError(f"Unknown decompiler: {self.decompiler}")
```

### Step 4: Update the settings options

In the frontend Settings page (`app/src/pages/SettingsPage.tsx`), add the new
decompiler to the dropdown options so users can select it.

### Step 5: Add a test

Add to `backend/tests/test_pipeline.py`:

```python
def test_fernflower_decompiler(tmp_path, sample_jar):
    pipeline = DecompilePipeline(
        jar_path=sample_jar,
        jar_name="test.jar",
        workspace_root=tmp_path,
        decompiler="fernflower",
    )
    # Test will depend on FernFlower being installed
```

---

## Decompiler Comparison

| Decompiler | Speed | Quality | Java Versions | Notes |
|---|---|---|---|---|
| **CFR** | Fast | Excellent | 6–17 | Default, best for Forge mods |
| **FernFlower** | Medium | Good | 5–17 | Used by IntelliJ, well-maintained |
| **Procyon** | Slow | Very good | 5–14 | Best output style, but slower & older JVM only |

CFR is recommended for most Forge mods (typically Java 6-8 bytecode). If
you see mangled output with CFR, try FernFlower as an alternative.

---

## CLI Signatures

Each decompiler has different CLI arguments:

**CFR**
```bash
java -jar cfr.jar <classes_dir> --outputdir <sources_dir>
```

**FernFlower**
```bash
java -jar fernflower.jar <classes_dir> <sources_dir>
```

**Procyon**
```bash
java -jar procyon.jar -jar <original.jar> -o <sources_dir>
```

Adjust each runner method accordingly.
