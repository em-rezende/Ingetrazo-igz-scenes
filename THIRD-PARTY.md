# Third-Party Notices

This project is distributed under **GPL-3.0-or-later** — see [LICENSE](LICENSE).

This file records notices for material that was **not** authored by the
project author, as required by the original licenses.

---

## 1. IngeTrazo

The toolbar/panel API used here belongs to **IngeTrazo** by the
Ingetrazo/Ingelibre project — <https://github.com/ingelibre/ingetrazo> —
also licensed **GPL-3.0-or-later**. The GPL text in [LICENSE](LICENSE) is
byte-identical to the one IngeTrazo ships. No IngeTrazo source code is
vendored in this repository; the plugin only calls its runtime API at load
time.

## 2. FFmpeg (optional, not bundled)

The optional **MP4** export spawns **FFmpeg** as an external process. FFmpeg
is a separate project by the FFmpeg team — <https://ffmpeg.org> — and is
**not** bundled with this extension. When FFmpeg is absent the plugin offers
to download an official/community build (from <https://www.gyan.dev/ffmpeg/>
or the BtbN builds on GitHub) into the user's local application-data folder
and stores the resulting path in its `config.json`. FFmpeg is distributed
under the GNU LGPL or GPL depending on the build; see
<https://ffmpeg.org/legal.html>. The PNG-sequence export needs no FFmpeg.

---

# Avisos de Terceiros

Este projeto é distribuído sob **GPL-3.0-or-later** — veja [LICENSE](LICENSE).

Este arquivo registra avisos de material que **não** foi criado pelo autor do
projeto, conforme exigido pelas licenças originais.

## 1. IngeTrazo

A API de barras de ferramenta/painéis usada aqui pertence ao **IngeTrazo**, do
projeto Ingetrazo/Ingelibre — <https://github.com/ingelibre/ingetrazo> —
também sob **GPL-3.0-or-later**. Nenhum código-fonte do IngeTrazo é
incorporado a este repositório; o plugin apenas chama a API em tempo de
execução.

## 2. FFmpeg (opcional, não incluído)

A exportação para **MP4** (opcional) executa o **FFmpeg** como processo
externo. O FFmpeg é um projeto separado da equipe do FFmpeg —
<https://ffmpeg.org> — e **não** é incluído nesta extensão. Quando o FFmpeg
está ausente, o plugin oferece baixar uma compilação oficial/da comunidade
(de <https://www.gyan.dev/ffmpeg/> ou das builds do BtbN no GitHub) para a
pasta local de dados do usuário e grava o caminho encontrado em seu
`config.json`. O FFmpeg é distribuído sob a GNU LGPL ou GPL, conforme a
compilação; veja <https://ffmpeg.org/legal.html>. A exportação como
sequência PNG não precisa do FFmpeg.
