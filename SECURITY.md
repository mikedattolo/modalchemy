# Security & Legal Notice

## Mod Decompilation — Legal Considerations

ModForge includes a decompilation pipeline for Minecraft Forge mod JAR files.
Users are solely responsible for ensuring their use complies with applicable laws
and mod licensing terms.

### Key points

| Topic | Guidance |
|---|---|
| **Personal / educational use** | Decompiling a mod for interoperability, learning, or debugging is generally permitted under the US DMCA §1201(f) interoperability exception and EU Directive 2009/24/EC Art. 6. This is **not** legal advice — consult a lawyer for your jurisdiction. |
| **Redistribution** | Do **not** redistribute decompiled source code of mods you do not own. ModForge never uploads or shares decompiled output. |
| **Mod licenses** | Many Forge mods are released under open-source licenses (MIT, GPL, etc.). Always check the mod's license before acting on decompiled code. |
| **Minecraft EULA** | Mojang's EULA and Forge's license govern your use of Minecraft and the modding framework. ModForge does not modify or redistribute Minecraft itself. |

## AI Training Data — Legal Considerations

ModForge includes tools to train pixel-art texture and JSON model generators.

### Dataset guidelines

- **Do not include copyrighted textures in this repository.**
  The repo ships no training images. Dataset preparation scripts document how
  to build a dataset from your own assets or from assets whose licenses permit
  derivative/ML use (e.g., CC0, CC-BY with compatible terms).
- **Fair use / ML exceptions** vary by jurisdiction. The US Copyright Office and
  EU AI Act treat ML training on copyrighted material differently. Understand
  your local rules.
- **Model weights** trained on permissively licensed or original data are yours
  to use. Weights trained on restrictively licensed data may carry obligations.

### What ships in the repo

| Artifact | Included? |
|---|---|
| Training code & scripts | Yes |
| Pre-trained model weights | No (too large; download instructions provided) |
| Sample / toy dataset | Placeholder scripts only — you supply data |
| Copyrighted Minecraft textures | **No — never** |

## Reporting Security Issues

If you discover a security vulnerability in ModForge itself (e.g., arbitrary
code execution via crafted JAR, prompt-injection in AI endpoints), please
report it privately:

1. **GitHub Security Advisories** — use the "Report a vulnerability" button on
   the repository's Security tab.
2. **Email** — security@modforge.example (placeholder; update when live).

Do **not** open a public issue for security vulnerabilities.

## Supply-Chain Security

- All Python dependencies are pinned with hashes where possible.
- Node dependencies use `package-lock.json` with integrity checks.
- CI runs `npm audit` and `pip-audit` on every PR.
- Tauri builds are reproducible and do not fetch remote code at runtime.
