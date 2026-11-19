# Development

Python 3.10+. Install `pip install -e .` and FFmpeg/ffprobe. Optional Tesseract English models for OCR.

```sh
python -m compileall -q src tests
python -m unittest discover -s tests -p 'test_*.py' -v
python -m liveclip doctor
```

- Runtime code lives under `src/liveclip/`; keep all external process invocations bounded and argument-vector based.
- Use synthetic media for tests. Never commit livestream data, tokens, API credentials, private photos/videos or the `Live_*` output folders.
- Changes affecting threshold/cooldown require scoring regression tests (scores are *not* probabilities).
- Never treat a skipped integration test as a passing FFmpeg test. Test reports distinguish executed/skipped status.
- GUI should only be updated on the Tkinter main thread; analyzer runs in a worker thread.

## Release gates

1. Static compile and unit/integration tests run locally with FFmpeg installed.
2. CLI and GUI smoke tests pass on intended operating systems.
3. Authorized live-stream capture exercised on at least one supported site.
4. Long-run CPU/disk/reconnection/interrupt and corrupt-media testing completed.
5. Verify third-party licenses and actual remote Actions status before claiming verified releases.

Only gate 1 is exercised by the synthetic local test suite in this environment; remote OS/live-stream gates remain manual.
