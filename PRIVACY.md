# Privacy and network behavior

NetScope has no telemetry, analytics, cloud account, API keys, advertising, update checks or external reporting. SQLite history, notes, settings and rotating logs stay on your PC. No credentials or packet payloads are collected. Reports and archives are saved only to destinations you choose.

Discovery requires an explicit opt-in. It sends bounded ICMP requests inside the selected private/local IPv4 subnet and reads the interface-scoped OS ARP table. Newly responding hosts may receive a targeted NetBIOS node-status query for a local hostname. Local hosts files are read; no external reverse DNS service is used. Diagnostic DNS queries ask for `localhost` only at a configured private resolver. The app does not itself connect to a public DNS resolver; your network's resolver implementation and forwarding configuration belong to its administrator.

Port checks are explicit, limited TCP connection attempts to a local device, with a fixed allowlist and rate limits. Local connection listing reads process and endpoint metadata; it does not access payloads, change connections or monitor other users remotely. Traffic readings are this PC's interface byte counters only.

There is no credential capture, MITM, ARP spoofing, deauthentication, packet injection, password cracking, exploit detection, banner harvesting, packet capture, remote-control server or hidden startup mechanism. Autostart is a visible optional setting using the current user's Windows Run registry entry. Closing to tray is configurable; pausing stops future scans.

The offline vendor dataset was bundled during development from Wireshark's public manufacturer list. The application has no downloader for it and makes no online vendor requests.

Local network identifiers (IP/MAC, hostnames, process names and user notes) are potentially personal data. CSV/JSON/HTML exports contain them. Exports leave your PC only if you share the files yourself. Reports escape user-entered HTML. Logs stay local and rotate at 1 MB with three backups. Data is not encrypted at rest: rely on Windows account permissions and disk encryption if needed.

Live and DEMO use separate databases and directories. DEMO does not probe the real network or list real connections. Explicit `--data-dir` paths still use separate mode subdirectories. Remove the mode directory only after fully quitting the app if you wish to erase data. Uninstall preserves local data so it can be recovered; autostart is removed by the optional installer.
