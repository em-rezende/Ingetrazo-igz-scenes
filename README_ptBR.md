# Extensão IngeTrazo — "Scenes" (Gerenciador de Cenas)

Uma **barra de ferramentas** e um **painel lateral** para o
[IngeTrazo](https://github.com/ingelibre/ingetrazo) que transformam posições
de câmera em uma lista ordenada de **cenas** (keyframes de câmera), as
reproduzem como uma **animação** suave de câmera e **exportam** o resultado
como sequência de imagens PNG ou vídeo MP4.

- **Autor:** Ezequiel M. Rezende
- **Data:** 2026-10-07
- **Versão:** 1.0.0
- **Licença:** [GPL-3.0-or-later](https://www.gnu.org/licenses/gpl-3.0.html)
  (mesma do IngeTrazo — ver [LICENSE](https://github.com/ingelibre/ingetrazo/blob/main/LICENSE))

---

![IngeTrazo com a barra "Scenes" e o painel lateral na tela](screenshots/igz-tb-scenes-main.png)

*A barra **Scenes** e o painel lateral **Cenas**. (Captura de tela a ser
adicionada antes da publicação.)*

---

## Arquivos

```
<plugins>/
├── igz_tb_scenes.py         # a extensão inteira
├── README.md                # este arquivo (inglês)
├── README_ptBR.md           # esta versão em português
├── LICENSE                  # texto completo da GPL-3.0
├── THIRD-PARTY.md           # avisos de terceiros
└── icons/
    ├── scene_add.svg              / scene_add_light.svg
    ├── scene_remove.svg           / scene_remove_light.svg
    ├── scene_remove_all.svg       / scene_remove_all_light.svg
    ├── scene_play.svg             / scene_play_light.svg
    ├── scene_stop.svg             / scene_stop_light.svg
    ├── scene_configure.svg        / scene_configure_light.svg
    ├── scene_export.svg           / scene_export_light.svg
    ├── scene_ffmpeg.svg           / scene_ffmpeg_light.svg
    └── scene_panel.svg            / scene_panel_light.svg
```

`igz_tb_scenes.py` é um **plugin autônomo de arquivo único**: define
`setup(app)`, então funciona quando colocado diretamente na pasta de plugins.
O empacotador do catálogo o envolve em um `.zip` de uma pasta só (ver
[Instalação](#instalação)).

---

## A barra "Scenes"

Cada botão captura ou reproduz keyframes de câmera. Um keyframe guarda
**eye** (posição), **target** (alvo) e **fov** (campo de visão); o painel
acrescenta a **permanência** (quanto tempo fica) e a **transição** (quanto
tempo leva para mover-se até a próxima) por cena.

| Botão                          | Ícone              |
|--------------------------------|--------------------|
| **Adicionar Cena Atual**       | `scene_add`        |
| **Remover Cena Selecionada**   | `scene_remove`     |
| **Limpar Cenas**               | `scene_remove`     |
| **Tocar Animação de Cenas**    | `scene_play`       |
| **Parar Animação**             | `scene_stop`       |
| **Configurar Tempos e Quadros**| `scene_configure`  |
| **Exportar Animação**          | `scene_export`     |
| **Dependências de Vídeo***     | `scene_configure`  |
| **Painel de Cenas** (toggle)   | `scene_panel`      |

\* O botão **Dependências de Vídeo** só aparece quando o FFmpeg não é
encontrado; com o FFmpeg presente a exportação MP4 já funciona.

A barra é adicionada à área **superior** (`igz_tb_scenes`), e os ícones
seguem a paleta clara/escura da interface (cada ícone tem uma variante
`_light`).

---

## O painel lateral "Cenas"

O painel é inserido como **aba** ao lado dos painéis laterais do próprio
IngeTrazo (Propriedades / BIM / Terreno / Renderizar / IA) quando o
hospedeiro permite; caso contrário, cai para um dock próprio ("Cenas"). Usa
divisores arrastáveis:

- **Cenas** — a lista (fixada em 5 linhas visíveis) mais **Adicionar**,
  **Remover** e **Limpar**.
- **Reprodução** — **Tocar**, **Parar**, a caixa **Repetir em loop** e um
  rótulo dinâmico de duração / número de quadros.
- **Tempos e Quadros** — FPS, interpolação, transição padrão, permanência
  padrão, uma tabela por cena (fixada em 4 linhas visíveis) e **Aplicar
  configuração**.
- **Exportação** — formato (Sequência PNG / MP4) e **Exportar Animação**.
- **Dependências de Vídeo** — o estado do FFmpeg e um botão **Configurar /
  Baixar…**.

O botão **Painel de Cenas** da barra mostra/esconde o painel (uma
`toggleViewAction` de dock, ou uma ação "ir para a aba Cenas").

---

## Cenas, o arquivo `.igz` e preferências

- **As cenas pertencem ao projeto.** São salvas **dentro** do documento
  `.igz` (`app.set_document_data`), então viajam com o arquivo e participam
  do desfazer/refazer. Abrir ou criar um documento recarrega-as.
- **Preferências** — FPS, interpolação, loop, transição/permanência padrão e
  tamanho de exportação — ficam em `config.json`, na pasta de dados do
  aplicativo (`.../igz_tb_scenes/config.json`), então projetos novos já
  começam com seus valores habituais.

---

## Interpolação da câmera

Há três modos em **Interpolação**:

- **Suave** — smoothstep (acelera/desacelera).
- **Linear** — velocidade constante.
- **Catmull-Rom** — uma spline pelos keyframes, para trajetórias de câmera
  curvas e orgânicas.

---

## Exportação

**Exportar Animação** pergunta o formato, o FPS e o **tamanho de saída**
(com trava de "manter proporção da tela" e um botão "tamanho da tela
atual"), depois renderiza cada quadro capturando o framebuffer:

- **Sequência de Imagens PNG** — grava `scene_00000.png`, … em uma pasta.
  Sem dependência externa.
- **Vídeo MP4** — renderiza os quadros PNG em uma pasta temporária e os
  junta com o **FFmpeg** (`libx264`, `yuv420p`, dimensões pares). Precisa do
  FFmpeg; o plugin o procura no caminho salvo, no `PATH`, na pasta local de
  dados e em locais comuns, e pode **baixar** uma compilação a pedido
  (**Configurar / Baixar…**).

O FFmpeg é opcional e **não é incluído** — veja
[THIRD-PARTY.md](THIRD-PARTY.md).

---

## Relação com o `igz_tb_camera`

Esta é uma extensão **independente**: **não** modifica o `igz_tb_camera`
(`OrbitPickerTool`, `ZAxisOverlay`, órbitas/helix e ajuste de Z continuam lá).
Ela apenas reaproveita o *padrão* de capturar `eye`/`target`/`fov` e de
capturar quadros. As duas podem ser instaladas ao mesmo tempo.

---

## Compatibilidade

- **IngeTrazo 0.5.7** (a versão com que foi testado).
- **PySide6 / Qt 6** — o plugin é Python puro; usa a câmera da viewport do
  aplicativo e o framebuffer capturável.
- Windows em primeiro lugar (o download do FFmpeg aponta para builds do
  Windows), mas a barra, o painel e a exportação PNG são multiplataforma.

### Idioma & internacionalização

Os tooltips da barra e os rótulos do painel estão, por ora, escritos em
**português** (`Adicionar`, `Tocar`, …), diferentemente da barra
*Styles/Shadows*, que espelha as strings traduzíveis do menu do IngeTrazo.
Tornar estes rótulos traduzíveis está listado em
[Melhorias futuras](#melhorias-futuras-opcional).

---

## Pontos frágeis (dependem do hospedeiro)

- **Descoberta da janela/viewport** — `setup(app)` localiza a janela
  principal por `QApplication.topLevelWidgets()` ou atributos de `app`, e a
  viewport pelo nome da classe. Hospedeiros incomuns podem exigir ajustes.
- **Encaixe do painel** — o "portador" (dock/aba) é encontrado por heurística
  (procura um grupo de abas intitulado Propriedades/BIM/Terreno/Renderizar/
  IA). Se nada casa, o painel cai para um dock próprio.
- **Nomes dos atributos da câmera** — `eye()`, `target` e `fov_deg` / `fov` /
  `field_of_view` são testados de forma defensiva.

### Se a API 0.x quebrar

Os pontos de integração são intencionalmente poucos: `setup(app)`, leitura/
escrita da câmera, `app.document_data` / `set_document_data`,
`on_document_changed` e `viewport.flash_status`. Se um IngeTrazo futuro mudar
isso, só esses pequenos auxiliares dentro de `igz_tb_scenes.py` precisarão
de ajuste.

---

## Instalação

### Manual (scripts / desenvolvimento)

1. No IngeTrazo, use **Extensões ▸ Abrir pasta de plugins** (ou abra a pasta
   de plugins do usuário: `%APPDATA%\IngeTrazo\plugins\` no Windows,
   `~/.local/share/ingetrazo/plugins/` no Linux).
2. Crie uma pasta chamada **`igz_tb_scenes`** dentro dela.
3. Copie para dentro **`igz_tb_scenes.py`**, a pasta **`icons/`** e o
   **ponto de entrada do pacote**
   (`packaging/igz_tb_scenes/__init__.py`, renomeado para `__init__.py`).
4. Reinicie o IngeTrazo. A barra **Scenes** aparece na área superior e o
   painel **Cenas** entra nos painéis laterais.

> A pasta **precisa** conter um `__init__.py` que carregue o
> `igz_tb_scenes.py` (o de `packaging/igz_tb_scenes/`). Um ponto de entrada
> ausente ou errado produz, silenciosamente, **nenhuma** barra e **nenhum**
> painel.

### Pelo catálogo de extensões do IngeTrazo

Empacotada para o catálogo da comunidade em
<https://ingetrazo.com/extensiones> (repositório
<https://github.com/ingelibre/ingetrazo-extensions>), que instala um único
`.zip` contendo uma pasta com um `__init__.py`. Gere esse arquivo com
`packaging/build_extension.ps1` (Windows) ou
`packaging/build_extension.py` (qualquer plataforma); ele sai em
`dist/igz_tb_scenes.zip`. Veja [`PUBLISHING.md`](PUBLISHING.md).

---

## Uso

1. Posicione a câmera na vista desejada e clique em **Adicionar Cena Atual**.
   Repita para cada vista.
2. Abra o painel **Cenas** para ajustar a **Permanência** e a **Transição** de
   cada cena, escolha o **FPS** e a **Interpolação** e clique em **Aplicar
   configuração**.
3. Clique em **Tocar** para visualizar; **Parar** interrompe. Marque
   **Repetir em loop** para uma pré-visualização em laço.
4. Clique em **Exportar Animação**, escolha **PNG** ou **MP4**, defina o
   tamanho e confirme.
5. Tudo é salvo junto com o `.igz`; reabra o arquivo e as cenas voltam.

---

## Melhorias futuras (opcional)

Nenhuma destas é necessária — a extensão funciona como está.

1. **Rótulos traduzíveis** — passar as strings da barra/painel pelo
   `core.i18n` do hospedeiro, em vez do português fixo.
2. **Subclasse `Tool`** — uma entrada "Cenas…" no menu **Extensions** com
   atalho, para o usuário reabrir a barra se ela for fechada.
3. **Migrar para `app.add_panel(...)`** para 100% de conformidade com a API
   (integração nativa com a bandeja lateral, em vez da busca heurística de
   hospedeiro).
4. **Suavização por cena** — um seletor de curva por keyframe.
5. **Linha do tempo na viewport** — um scrubber e um atalho "adicionar
   atual".

---

## Licença

GPL-3.0-or-later — a mesma licença do IngeTrazo.
Avisos de terceiros ficam em [THIRD-PARTY.md](THIRD-PARTY.md).

Ver <https://www.gnu.org/licenses/gpl-3.0.html>.

Copyright (C) 2026 Ezequiel M. Rezende.

Este programa é software livre: você pode redistribuí-lo e/ou modificá-lo
sob os termos da GNU General Public License, versão 3 ou posterior,
conforme publicada pela Free Software Foundation.

Este programa é distribuído na esperança de ser útil, mas **sem qualquer
garantia**; sem mesmo a garantia implícita de **comercialização** ou
**adequação a um propósito específico**. Veja a GNU General Public License
para mais detalhes.

---

### Tabela de correspondência (EN ↔ PT-BR)

| Seção | Inglês | Português |
|---|---|---|
| Título | Extensions — "Scenes" (Scene Manager) | Extensão — "Scenes" (Gerenciador de Cenas) |
| Arquivos | Files | Arquivos |
| Barra | The "Scenes" Toolbar | A barra "Scenes" |
| Painel | The "Cenas" Side Panel | O painel lateral "Cenas" |
| Documento | Scenes, the `.igz` file and preferences | Cenas, o arquivo `.igz` e preferências |
| Interpolação | Camera interpolation | Interpolação da câmera |
| Exportação | Export | Exportação |
| Compatibilidade | Compatibility | Compatibilidade |
| Pontos frágeis | Fragile points | Pontos frágeis |
| Instalação | Installation | Instalação |
| Uso | Usage | Uso |
| Melhorias futuras | Future improvements | Melhorias futuras |
| Licença | License | Licença |
