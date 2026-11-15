# Publicar no catálogo de Extensões do IngeTrazo

> **Status: v1.1.0 pronta para publicar.** O `.zip` foi reconstruído a partir
> do pacote refatorado, o `sha256` da ficha foi atualizado e a Release `v1.1.0`
> (asset `igz_tb_scenes.zip`) é o próximo passo; o catálogo ainda aponta para a
> `v1.0.0` (pull request <https://github.com/ingelibre/ingetrazo-extensions/pull/55>).

Este documento (PT) e a seção em inglês mais abaixo descrevem como publicar
esta extensão no catálogo <https://github.com/ingelibre/ingetrazo-extensions>
(mostrado em <https://ingetrazo.com/extensiones>).

---

## O que já está pronto

| Item | Onde | Observação |
|---|---|---|
| Código | `igz_tb_scenes/` | Pacote Python: `__init__.py` define `setup(app)` e o código fica em `core/`. |
| Empacotador | `packaging/build_extension.py` (canônico, multi-plataforma) e `packaging/build_extension.ps1` (Windows; delega ao Python quando disponível) | Gera um `.zip` determinístico com **uma** pasta de topo `igz_tb_scenes/`. |
| Ponto de entrada do pacote | `igz_tb_scenes/__init__.py` | Define `setup(app)`, carrega o `core/` e resolve as traduções de `i18n/`. |
| Artefato | `dist/igz_tb_scenes.zip` | Gerado pelo script; ele imprime o `sha256`. |
| Ficha do catálogo | `ingetrazo-extensions-submission/extensions/igz_tb_scenes.toml` | Copiar para `extensions/igz_tb_scenes.toml` no repositório do catálogo. |
| Captura de tela | `ingetrazo-extensions-submission/screenshots/igz_tb_scenes.png` | Enviada no pull request do catálogo (PR #55). |

O `.zip` contém exatamente uma pasta de topo:

```
igz_tb_scenes/
├── __init__.py          # setup(app) + i18n
├── core/*.py            # config, controller, dialogs, ffmpeg, model, panel, toolbar...
├── i18n/*.json          # pt-BR, es, it, de, fr, zh (en = idioma-fonte)
├── icons/*.svg
├── LICENSE
├── README.md
├── README_ptBR.md
└── THIRD-PARTY.md
```

O catálogo instala **um arquivo por extensão**: um `.py`, ou um `.zip` com
**uma** pasta contendo um `__init__.py` (ver `TEMPLATE.toml` no repositório do
catálogo). Por isso esta extensão, que traz um pacote com módulos, traduções e
ícones, usa o formato `.zip`.

---

## Passos para publicar (quando autorizar)

1. **Confirme as alterações locais e faça o commit.**
   ```powershell
   git add -A
   git commit -m "chore: release 1.1.0 (package refactor) to the IngeTrazo extension catalog"
   ```

2. **Reconstrua o artefato** — obrigatório aqui, porque a estrutura de pastas mudou:
   ```powershell
   python packaging\build_extension.py
   ```
   Anote o `sha256` impresso e atualize-o em
   `ingetrazo-extensions-submission/extensions/igz_tb_scenes.toml`.

3. **Envie o código para o GitHub e crie a etiqueta `v1.1.0`.**
   ```powershell
   git push origin main
   git tag v1.1.0
   git push origin v1.1.0
   ```

4. **Crie a Release `v1.1.0`** em
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
   - [x] `download` aponta para uma **tag** (`v1.1.0`), não para uma branch.
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

> **Status: v1.1.0 ready to publish.** The `.zip` was rebuilt from the
> refactored package, the entry's `sha256` was refreshed and the `v1.1.0`
> Release (asset `igz_tb_scenes.zip`) is the next step; the catalog still points
> at `v1.0.0` (pull request
> <https://github.com/ingelibre/ingetrazo-extensions/pull/55>).

Everything needed is in place (code, a `.zip` builder, the package entry, the
catalog entry and a screenshot). These steps are:

1. Commit locally (`git add -A; git commit -m "chore: release 1.1.0 ..."`).
2. Rebuild: `python packaging/build_extension.py` (the `.ps1` delegates to it)
   and copy the printed `sha256` into the entry.
3. `git push origin main`, then `git tag v1.1.0` and `git push origin v1.1.0`.
4. Create the **v1.1.0** GitHub Release and attach
   `dist/igz_tb_scenes.zip` as an asset named exactly `igz_tb_scenes.zip`.
5. In <https://github.com/ingelibre/ingetrazo-extensions>, copy
   `ingetrazo-extensions-submission/extensions/igz_tb_scenes.toml` and the
   screenshot into place, then **Create pull request**.
6. Fill in the PR template checklist.

The **sha256** in the entry must match `dist/igz_tb_scenes.zip` byte-for-byte;
rebuilding with `packaging/build_extension.py` prints the value to paste. Note
that the optional **MP4** export **downloads and runs FFmpeg** (needs network);
the **PNG** export does not.
