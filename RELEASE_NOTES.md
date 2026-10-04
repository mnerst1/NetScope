# NetScope v1.0.0 — Day 014

Local-first Windows desktop network monitoring built with Python 3.12 and PySide6 / Qt 6.

- Nine pages: Overview, Devices, Network Map, Traffic, Connections, Events, Diagnostics, Reports, Settings.
- Authorized local IPv4 discovery, MAC/hostname/vendor metadata where available, device names/types/tags, trust/favorites and notes.
- SQLite event and latency history, sampled availability/packet loss, local interface traffic and read-only process connections.
- Diagnostics, CSV/JSON/HTML exports, network snapshots and comparisons.
- Light/Dark/System, six styles, custom accents, tray and optional per-user autostart.
- 23 languages with 122/122 canonical keys tested; Arabic/Persian RTL. Independent native-speaker linguistic review is still pending.
- Settings → Demo records fills the views with random synthetic data in a separate database. Settings → Real data returns to live mode.

## Windows downloads

- **NetScope-Setup-v1.0.0.exe** — per-user installer, Start Menu, optional Desktop shortcut, uninstall. No Python or Visual Studio required.
- **NetScope-v1.0.0-Windows-x64.zip** — recommended portable onedir build. Extract and launch `NetScope/NetScope.exe`; keep `_internal` beside it.
- **NetScope-v1.0.0-Windows-x64.exe** — optional standalone onefile build. Initial startup takes longer while Qt extracts.
- **NetScope-v1.0.0-Windows-x64-OneFile.zip** — onefile EXE with documentation and license notices.
- **NetScope-v1.0.0-source.zip** — clean source project for VS Code.
- **SHA256SUMS.txt** — SHA-256 hashes of downloadable artifacts.

## Verification and limits

37 automated tests passed. Both Windows binaries passed isolated rich-DEMO startup tests. The installer was compiled with Inno Setup 6.7.3. Successful discovery on a real network cannot be verified in the development execution sandbox; use TEST_CHECKLIST.md on your authorized network and a clean Windows PC.

Discovery is opt-in, private IPv4 /24 or smaller, at most 254 hosts. ICMP blocking/sleep can look offline. Availability is sampled probe success, not continuous hardware uptime. Traffic is this PC's selected interface, not per-device bandwidth. The map is explicitly logical, not physical topology. Port checks require an explicit user action and a fixed, rate-limited local allowlist.

No cloud accounts, API keys, telemetry or packet payload capture. Windows executables are unsigned. Full source, rebuild instructions, privacy notes and third-party notices are included in the repository and archives.
