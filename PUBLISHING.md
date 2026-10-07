# Publicar no catálogo de Extensões do IngeTrazo

> **Status: v1.0.0 preparada, ainda NÃO publicada.** Este guia descreve os
> passos para publicar esta extensão no catálogo.

Este documento (PT) e a seção em inglês mais abaixo descrevem como publicar
esta extensão no catálogo <https://github.com/ingelibre/ingetrazo-extensions>
(mostrado em <https://ingetrazo.com/extensiones>).

---

## O que já está pronto

| Item | Onde | Observação |
|---|---|---|
| Código | `igz_tb_scenes.py` | Plugin de arquivo único; define `setup(app)`. |
| Empacotador | `packaging/build_extension.ps1` (Windows) e `packaging/build_extension.py` (multi-plataforma) | Gera um `.zip` determinístico com **uma** pasta de topo `igz_tb_scenes/`. |
| Ponto de entrada do pacote | `packaging/igz_tb_scenes/__init__.py` | Define `setup(app)` e carrega o `igz_tb_scenes.py` por caminho de arquivo. |
| Artefato | `dist/igz_tb_scenes.zip` | Gerado pelo script; ele imprime o `sha256`. |
| Ficha do catálogo | `ingetrazo-extensions-submission/extensions/igz_tb_scenes.toml` | Copiar para `extensions/igz_tb_scenes.toml` no repositório do catálogo. |
| Captura de tela | `ingetrazo-extensions-submission/screenshots/igz_tb_scenes.png` | **A adicionar** antes da publicação. |

O `.zip` contém exatamente uma pasta de topo:

```
igz_tb_scenes/
├── __init__.py          # setup(app)
├── igz_tb_scenes.py
├── icons/*.svg
├── LICENSE
├── README.md
├── README_ptBR.md
└── THIRD-PARTY.md
```

O catálogo instala **um arquivo por extensão**: um `.py`, ou um `.zip` com
**uma** pasta contendo um `__init__.py` (ver `TEMPLATE.toml` no repositório do
catálogo). Por isso esta extensão, que traz um módulo e uma pasta de ícones,
usa o formato `.zip`.

---

## Passos para publicar (quando autorizar)

1. **Confirme as alterações locais e faça o commit.**
   ```powershell
   git add -A
   git commit -m "chore: prepare 1.0.0 for the IngeTrazo extension catalog"
   ```

2. **(Opcional) Reconstrua o artefato** — só é preciso se você mudou o código:
   ```powershell
   powershell -ExecutionPolicy Bypass -File packaging\build_extension.ps1
   ```
   Anote o `sha256` impresso e atualize-o em
   `ingetrazo-extensions-submission/extensions/igz_tb_scenes.toml`.

3. **Envie o código para o GitHub e crie a etiqueta `v1.0.0`.**
   ```powershell
   git push origin main
   git tag v1.0.0
   git push origin v1.0.0
   ```

4. **Crie a Release `v1.0.0`** em
   <https://github.com/em-rezende/Ingetrazo-igz-scenes/releases/new> e
   **anexe `dist/igz_tb_scenes.zip` como asset** (nome exatamente
   `igz_tb_scenes.zip`).

5. **Abra o pull request no repositório do catálogo** (sem Git, pelo
   navegador):
   - *Add file ▸ Create new file* → `extensions/igz_tb_scenes.toml`, cole o
     conteúdo de
     `ingetrazo-extensions-submission/extensions/igz_tb_scenes.toml`.
   - *Add file ▸ Upload files* → envie a captura para `screenshots/`, com o
     nome `igz_tb_scenes.png` (o mesmo do campo `screenshot`).
   - **Propose changes ▸ Create pull request**.

6. **Responda o checklist** do template do PR:
   - [x] Um arquivo `extensions/igz_tb_scenes.toml`, copiado de
     `TEMPLATE.toml`.
   - [x] `download` aponta para uma **tag** (`v1.0.0`), não para uma branch.
   - [x] A licença em `license` é a do código (GPL-3.0-or-later).
   - [x] `reviewed.toml` **não** foi tocado (só mantenedores).
   - Descreva no PR: a exportação **MP4** (opcional) **baixa e executa o
     FFmpeg** e, para isso, **acessa a rede**; a exportação **PNG** não usa
     rede nem processos externos.

---

## Detalhes que você pode querer ajustar

- **Versão do IngeTrazo** (`ingetrazo = "0.5.7"`): use a versão com que você
  realmente testou.
- **Tags** (`tags = [...]`): só são válidas `architecture`, `bim`,
  `structures`, `terrain`, `drawing`, `analysis`, `import-export`,
  `rendering`, `fabrication`, `productivity`, `education`, `other`.
- **Captura de tela**: a sugestão do catálogo é ~1200×750 e o limite é
  600 KB.

---

# Publishing to the IngeTrazo extension catalog (EN)

> **Status: v1.0.0 prepared, not yet published.** This guide covers the
> publication steps.

Everything needed is in place (code, a `.zip` builder, the package entry, the
catalog entry and a screenshot placeholder). To publish, once you authorise
it:

1. Commit locally (`git add -A; git commit -m "chore: prepare 1.0.0 ..."`).
2. (Only if the code changed) rebuild: `packaging\build_extension.ps1` and
   copy the printed `sha256` into the entry.
3. `git push origin main`, then `git tag v1.0.0` and `git push origin v1.0.0`.
4. Create the **v1.0.0** GitHub Release and attach
   `dist/igz_tb_scenes.zip` as an asset named exactly `igz_tb_scenes.zip`.
5. In <https://github.com/ingelibre/ingetrazo-extensions>, copy
   `ingetrazo-extensions-submission/extensions/igz_tb_scenes.toml` and the
   screenshot into place, then **Create pull request**.
6. Fill in the PR template checklist.

The **sha256** in the entry must match `dist/igz_tb_scenes.zip` byte-for-byte;
rebuilding with `packaging/build_extension.ps1` (or
`packaging/build_extension.py`) prints the value to paste. Note that the
optional **MP4** export **downloads and runs FFmpeg** (needs network); the
**PNG** export does not.
