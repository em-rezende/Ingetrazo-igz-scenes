# Submission bundle — IngeTrazo extension catalog

> **Submission bundle for the IngeTrazo extension catalog** (v1.0.0). These
> are the files to copy into a pull request of
> <https://github.com/ingelibre/ingetrazo-extensions> to publish the
> extension.

Copy these things into the catalog repository:

| From here | To the catalog repository |
|---|---|
| `extensions/igz_tb_scenes.toml` | `extensions/igz_tb_scenes.toml` |
| `screenshots/igz_tb_scenes.png` *(to be added)* | `screenshots/igz_tb_scenes.png` |

Then open the pull request (browser: *Add file ▸ Create new file* and *Add
file ▸ Upload files* → **Propose changes** → **Create pull request**) and fill
in the template checklist.

## Before you submit

- The `download` URL points at the **v1.0.0** GitHub Release asset
  `igz_tb_scenes.zip`, so create that tag/release in this repository first and
  upload `dist/igz_tb_scenes.zip` as the asset with that exact name.
- The `sha256` in the entry must match that asset byte-for-byte. Rebuild with
  `packaging/build_extension.ps1` (or `packaging/build_extension.py`) if the
  code changed, and paste the value it prints.
- Add a screenshot named `igz_tb_scenes.png` (the `screenshot` field refers to
  it); the extension shows a top toolbar and a side panel.

Full, step-by-step instructions are in [`../PUBLISHING.md`](../PUBLISHING.md).
