# Local wheels for Chaquopy

Chaquopy’s Android pip cannot install some packages from PyPI as-is:

- `pyaes` — sdist only (no `py3-none-any` wheel on PyPI)
- `pydantic-core` — needs Android-native wheels (Rust)

Wheels in this directory are passed to pip via `--find-links`.

`pyaes` is committed here. `pydantic-core` Android wheels are built in CI
(see `.github/workflows/release.yml`) and placed here before Gradle runs.
