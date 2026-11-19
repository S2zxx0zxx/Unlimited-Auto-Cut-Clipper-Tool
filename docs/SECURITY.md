# Security and responsible use

- **Authorized sources only:** This app does not implement login automation, DRM circumvention or private-stream downloads. Recording or redistributing streams without permission can infringe rights.
- **Local processing:** No paid API. The app itself makes requests through Streamlink to user-selected sources and may fetch Python dependencies on first installation. There is no auto-upload feature.
- **URL input:** HTTP(S) with hostname only; credential-in-URL and literal loopback/private/reserved IP addresses are rejected. Hostname DNS rebinding and hostnames resolving to private networks are **not guaranteed blocked**; don't process untrusted URLs in privileged environments. Streamlink may follow redirects and make additional requests.
- **Subprocesses:** Uses Python argument arrays, not `shell=True`. FFmpeg, ffprobe, Streamlink and optional Tesseract must be trustworthy and updated. Media decoding has a nonzero vulnerability surface.
- **Data retention:** Source videos, SQLite database, report manifests, exports and user review labels persist on disk until the user deletes them. Logs can leak platform URLs. No clip is automatically deleted. Avoid storing confidential recordings in shared folders.
- **Resource limits:** Disk free-space safeguards are approximate; high-bitrate streams, malformed inputs, temporary files and multiple sessions still consume substantial CPU/disk. Use OS-level permissions/quotas on shared hosts.
- **Report security concerns:** Open a GitHub private vulnerability report if enabled, otherwise contact the repository owner through a non-public channel before publishing exploit details.

Do not place private stream tokens in CLI arguments: shell history and process monitors can reveal them.
