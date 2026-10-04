# NetScope 1.0.0 — verification record

Date: 2026-10-04. Windows 11 x64, Python 3.12.14, PySide6 6.9.3 / Qt 6.9.3, psutil 7.1.0, PyInstaller 6.16.0. No Visual Studio or .NET UI toolchain used.

## Completed

- Python compileall: success.
- Automated suite: **37 passed**. Includes subnet boundaries/reserved networks, parsers, DHCP merge/stale ARP/address reuse, settings/SQLite reopen, observations and retention, snapshot changes, strict port allowlist and delays, offline vendor/randomized-MAC rules, export Unicode/escaping and UI startup.
- Locale validation: **23 locales, 122/122 keys each**, exact key equality, nonempty values. UI language changes were exercised across all nine pages. Arabic/Persian set RTL. No individual-string English fallback.
- Appearance: Qt tests exercise 3 themes × 6 styles. Native Windows screenshots visually inspected for Russian Overview/device detail, Kazakh Devices/light theme, English map, and Arabic RTL Settings. Minimum 1280×720 logical layout inspected at the host's 125% scaling. Other scaling factors and languages still require human visual review.
- Source startup: isolated DEMO mode opened and automatically exited successfully.
- Real interface enumeration: Windows IP Helper API identified the active Wi-Fi adapter and its IPv4 gateway without WMI or elevation. Host execution policy restricts DNS/ICMP visibility.
- **Onedir EXE actually built**, platform plugin `qwindows.dll`, Qt translations, all app locales/icons and the offline 40,033-prefix vendor dataset included. Isolated EXE smoke startup returns **exit code 0** and creates a window screenshot.
- **Onefile EXE actually built** and smoke-started, **exit code 0**. Offered as an optional convenience archive; onedir remains preferred. Clean-machine and antivirus behavior not verified.
- Source-only archive excludes virtual environments, caches, runtime databases/logs, build/dist/release, generated onefile spec and environment files. Archive inventory and CRC verified.

## Not verified / intentionally limited

- Successful live ICMP/discovery on this host: execution sandbox returns a system ping failure even for the local gateway. Real-network discovery, device notifications and local TCP port checks need your own authorized-network test. No successful live-device results are claimed.
- Clean Windows deployment without Python and different firewall/antivirus policies.
- Independent linguistic review by native speakers: automated **100% canonical coverage is confirmed**, semantic perfection is not claimed.
- HiDPI factors other than the host's 125%; unusually long custom text and all native OS dialog translations.
- Inno Setup 6.7.3 installer compiled; see the release artifacts.
- Continuous hardware uptime, per-device bandwidth and physical topology: these are not measured. Availability is ICMP sample success, traffic is this PC's selected adapter, the map is explicitly logical.
- Native acrylic blur: Glass uses stable colors/borders rather than platform backdrop effects.
- No packet capture, external API, cloud dependency, telemetry.

Use TEST_CHECKLIST.md before wider release. This is a locally testable 1.0.0 implementation, not a claim of field certification.

## Demo records update

The Settings button and return-to-live flow were tested through Qt. All nine views receive synthetic data; generation never calls network commands. Tests verify live database contents remain unchanged, a live repository refuses demo replacement, randomized generations differ, and settings are retained. Updated source and both Windows binaries were rebuilt; rich DEMO startup was exercised using `--smoke-test --demo-records`.
