# Submission bundle — IngeTrazo extension catalog

> **Submission bundle for the IngeTrazo extension catalog** (v1.0.0). These
> are the files submitted in the catalog pull request
> <https://github.com/ingelibre/ingetrazo-extensions/pull/55>.

The files below go into the catalog repository:

| From here | To the catalog repository |
|---|---|
| `extensions/igz_tb_scenes.toml` | `extensions/igz_tb_scenes.toml` |
| `screenshots/igz_tb_scenes.png` | `screenshots/igz_tb_scenes.png` |

The pull request (<https://github.com/ingelibre/ingetrazo-extensions/pull/55>)
was opened with the template checklist filled in.

## Preconditions (all met)

- The `download` URL points at the **v1.0.0** GitHub Release asset
  `igz_tb_scenes.zip`, so create that tag/release in this repository first and
  upload `dist/igz_tb_scenes.zip` as the asset with that exact name.
- The `sha256` in the entry must match that asset byte-for-byte. Rebuild with
  `packaging/build_extension.ps1` (or `packaging/build_extension.py`) if the
  code changed, and paste the value it prints.
- Add a screenshot named `igz_tb_scenes.png` (the `screenshot` field refers to
  it); the extension shows a top toolbar and a side panel.

Full, step-by-step instructions are in [`../PUBLISHING.md`](../PUBLISHING.md).
