# Development Notes

Notes for anyone (human or automated) working on this repo.

## This is a fork

Fork of [jellyfin/jellycon](https://github.com/jellyfin/jellycon), rebranded
**"Jellyvin"**, with custom features added on the `dj-dev` branch. It's a thin
Kodi frontend for a Jellyfin server.

- Plugin entry point: `default.py` → `main_entry_point()` in
  `resources/lib/functions.py` (a `mode`-based URL router).
- Background service: `service.py` (started at login).
- Core logic lives in `resources/lib/`.

## `addon.xml` is GENERATED — do not hand-edit it

`addon.xml` is a build artifact. Any manual edit is overwritten on the next
build. It is produced by `build.py` from two sources:

| Field(s) | Source |
| --- | --- |
| `name`, `provider-name`, `<source>`, and other static metadata | `.config/template.xml` |
| `version`, `<requires>` dependencies, changelog (`<news>`) | `release.yaml` |

- Final version string = `release.yaml` `version` + `+py3` (e.g. `1.0.0+py3`).
- To change branding → edit `.config/template.xml`.
- To change version / dependencies / changelog → edit `release.yaml`.

## Building

```sh
# Use the bundled virtualenv's Python (build.py needs pyyaml).
./jellycon_env/bin/python build.py            # production build
./jellycon_env/bin/python build.py --dev      # dev build (skips folder filtering)
./jellycon_env/bin/python build.py --version py2   # py2 dependency set
```

Outputs:
- Regenerates `addon.xml` in place.
- Produces `plugin.video.jellycon+py3.zip` (installable add-on).

If `pyyaml` is missing: `./jellycon_env/bin/pip install pyyaml`
(see `requirements-dev.txt`).

## Known gotchas

- `build.py`'s `folder_filter` excludes `.git`, `__pycache__`, `venv`, etc. but
  **not** `jellycon_env/`, so the entire virtualenv currently gets zipped into
  the artifact, bloating it (~8 MB). Add `jellycon_env` to the filter list in
  `build.py` for a clean distributable.
- This repo is checked out inside Kodi's live `addons/` directory, so edits run
  directly in Kodi.

## Linting

`flake8` (config in `tox.ini`, pep8 import order). Dev deps in
`requirements-dev.txt`.
