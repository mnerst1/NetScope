# Verification checklist

## Automated, completed in this development environment

- [x] Python 3.12 compileall.
- [x] 37 pytest cases: subnet and reserved-range guards, MAC/ARP/ping parsers, device merge/DHCP reuse/stale ARP, database reopen/settings, retention, snapshots, port constraints/rate delay, exports/HTML escaping and vendor handling.
- [x] 23 locales × 122 canonical nonempty keys, exact set equality, no missing/extra keys.
- [x] Qt offscreen tests: all nine pages and 23 language changes, including RTL, 3 themes × 6 styles, demo diagnostics and reports.
- [x] Demo records button: all pages populated, regenerates random data, returns to live, live DB unchanged, network calls forbidden in the scenario.
- [x] Source GUI startup smoke test, screenshot, successful exit.
- [x] Windows IP Helper adapter enumeration: real active Wi-Fi gateway identified.
- [x] PyInstaller onedir build and EXE startup smoke test, exit code 0, screenshot.

See `VERIFICATION.md` for final artifact results. Automated completeness proves catalog coverage, not linguistic review. Smoke test runs DEMO and never scans the real network. This host's execution sandbox does not permit successful ICMP, so successful real-network discovery is not claimed here.

## On your Windows PC before wider distribution

- [ ] Run the entire onedir folder on a clean Windows 10/11 x64 PC without Python, as a standard user.
- [ ] Start live mode. Verify no discovery occurs before consent, correct adapter/gateway/DNS, then allow monitoring on your own network.
- [ ] Compare responding devices with your router's inventory; test a firewall-blocked/sleeping device and understand the ICMP limitation.
- [ ] Disconnect/reconnect an owned device. Confirm transitions, first/last seen, history gaps and notification toggles.
- [ ] Rename/type/tag/trust/favorite a device and write a note; quit and reopen. Confirm persistence.
- [ ] Confirm DHCP IP change preserves MAC identity and notes; changed MAC at the same IP creates a different record.
- [ ] Run a device's explicit port check. Confirm the fixed 12-port set, cooldown and prohibition of out-of-subnet/public targets.
- [ ] Inspect local connections with process names; test permission-restricted process information without requiring administrator rights.
- [ ] Compare upload/download with Task Manager on the selected adapter; switch adapters and check that counters reset.
- [ ] Run diagnostics with private DNS and with public/missing DNS. Confirm skip versus failure is clear.
- [ ] Export devices CSV/JSON, history CSV/JSON and HTML. Open Unicode CSV in Excel; verify DEMO labels in synthetic exports.
- [ ] Save two snapshots with an intervening device change and compare added/removed/changed rows.
- [ ] Change all languages; native speakers should review wording, long labels, scripts and RTL layout.
- [ ] Light/Dark/System and every style/accent, including a system-theme change while running.
- [ ] 1280×720 logical viewport; larger monitors at 100%, 125%, 150%, 175% and 200% scaling, resize and scroll; inspect device details and long translations.
- [ ] Ctrl+K, keyboard navigation, F5, sorting IP/latency/availability, context menus and search filters.
- [ ] Pause, manual scan, tray close/show/quit, notifications disabled, optional autostart enable/disable. Verify explicit autostart only.
- [ ] Force-close during a scan, reopen, check DB consistency and local rotating logs.
- [ ] Long run: scan intervals do not overlap; retention cleanup bounds time-series rows and snapshots (inventory/notes intentionally remain).
- [ ] Optional onefile on a separate PC; optional Inno installer installation/shortcuts/uninstall, preserving database and removing autostart.

Repository and v1.0.0 release are published at https://github.com/mnerst1/NetScope.
