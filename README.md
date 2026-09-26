# Home Circuit — Company Story (DRAFT / Pre-visualization)

A 2:00 cinematic **pre-visualization** of the Home Circuit company introduction
video, rendered entirely from code. Every picture, product, logo, sound and
the Thai guide voice in this draft are **conceptual placeholders** made for
client review. They are built so that real footage, product renders, the real logo, a
professional narration and licensed music can replace them later without
rewriting the edit.

**Output:** `output/home_circuit_company_story_draft.mp4`
(1920×1080, 16:9, 30 fps, H.264 High, AAC 48 kHz stereo, Thai subtitles burned in)

Sidecar files are written next to it:

- `…draft.th.srt`: Thai subtitles (SRT)
- `…draft.th.ass`: Thai subtitles, styled
- `output/timeline_manifest.json`: every scene, shot and VO line with its time code

---

## Render it again

```bash
# system tools (Debian/Ubuntu)
sudo apt-get install -y ffmpeg espeak-ng        # ffmpeg must have libx264 + libass
pip install -r requirements.txt

./render.sh                  # = python3 -m scripts.build_assets && python3 -m src.render
```

On 4 CPU cores a full render takes about 8–10 minutes. Useful variants:

| Command | What it does |
|---|---|
| `python3 -m src.render --scenes 03,05` | Re-renders only scenes 03 and 05, reuses the other cached clips, then remixes and remuxes |
| `python3 -m src.render --preview 22.0,95.5` | Writes still PNGs at those global times to `output/build/stills/` |
| `python3 -m src.render --audio-only` | Rebuilds VO, music, SFX, the mix and the subtitles, then remuxes. The picture is not re-rendered |
| `python3 -m src.render --force-vo` | Regenerates the scratch TTS voice even if `audio/voiceover/*.wav` exist |
| `python3 -m src.render --keep-music` | Uses your own `audio/music/music_score.wav`, such as a licensed track, instead of the generated score |
| `python3 -m src.render --no-burn-subs` | Renders a clean picture. Subtitles stay available as `.srt`/`.ass` |
| `python3 -m scripts.build_assets --force` | Regenerates all procedural plates, product renders and the logo |
| `python3 -m scripts.qc` | Checks the output (format, duration, streams) and writes a contact sheet |

---

## Project structure

```
src/
  config.py                 format, palette, fonts, encoding settings
  timeline.py               scene order (global start times derive from scene lengths)
  render.py                 parallel frame renderer → scene clips → concat → mix → mux
  plates.py                 conceptual still "plates" (layered for parallax)
  engine/
    canvas.py               cairo/PIL helpers, glow, grading, vignette, grain, motion blur
    camera.py               2.5D camera: Ken Burns, push-in, pan, multi-layer parallax
    scene.py                Scene / Shot / Overlay / VO / SFX data model
    text.py                 typography + animations (mask, track, fade, scale, slam, type)
    pcb.py                  PCB traces, animated trace drawing, boards, schematic, CAD view
    props.py                illustrated props (people silhouettes, tools, drone, gateway…)
    overlays.py             DRAFT VISUAL badge, labels, callouts, scope, code editor
    product.py              conceptual HC GW-01 gateway renders
    logo.py                 TEMPORARY logo concept + animation
  scenes/
    common.py               shared overlays, trace wipes, plate-space animation helpers
    s01_hook.py … s08_ending.py   one module per scene (01_HOOK … 08_ENDING)
  audio/
    voiceover.py            scratch Thai TTS (espeak-ng) fitted to each VO slot
    music.py                generative 120 BPM score following the scene structure
    sfx.py                  synthesized SFX library
    mix.py                  VO / music / SFX layers, ducking, loudness (-16 LUFS)
    subtitles.py            Thai ASS + SRT (max two lines)
scripts/
  build_assets.py           writes plates / products / logo into assets/ (keeps existing files)
  make_fonts.py             builds "HC Thai Sans" (Noto Sans + Noto Sans Thai merged)
  qc.py                     output checks + contact sheet
assets/
  images/                   plates: <name>__bg.png, __mid.png, __fx.png, __fg.png
  products/                 gateway_3q.png, gateway_front.png, gateway_pcb.png
  logo/                     hc_logo_mark.png, hc_logo_full.png  (TEMPORARY)
  graphics/  footage/       reserved for real graphics / live-action footage
  fonts/                    Inter, Noto Sans Mono, HC Thai Sans (all SIL OFL)
audio/
  voiceover/                vo01.wav … vo14.wav (scratch), VO_SCRIPT.md, _scratch.json
  sfx/                      relay_click.wav, whoosh.wav, drone.wav, …
  music/                    music_score.wav (generated at render time)
output/
  home_circuit_company_story_draft.mp4 (+ .th.srt, .th.ass, timeline_manifest.json)
  build/                    cache: scene chunks, stems, mix, stills (git-ignored)
```

## Timeline (2:00)

| Scene | Start | Length | Content |
|---|---|---|---|
| 01_HOOK | 0:00 | 7.5 s | black → relay click → 0.7–0.85 s macro cuts → **IT STARTED FROM A HOME.** |
| 02_BEGINNING | 0:07.5 | 17 s | Thai house at dusk → warm home workshop → **NEED IT?** → **BUILD IT.** (on the music hit) |
| 03_IDEA_TO_HARDWARE | 0:24.5 | 17.5 s | sketch → schematic → PCB layout → PCB → soldering → firmware → test → prototype, linked by green trace wipes and a pipeline bar (match cuts on one board outline) |
| 04_PROJECTS | 0:42 | 19 s | freelance chat → project network → IoT, GATEWAY, DRONE / UAV, ENGINEERING PROJECTS, SMART AGRICULTURE, EMBEDDED SYSTEMS |
| 05_PHILOSOPHY | 1:01 | 19 s | concept gateway hero → PCB callouts → developer connects + codes → **BUILD. MODIFY. DEVELOP.** → **HARDWARE MADE FOR DEVELOPERS.** |
| 06_CAPABILITIES | 1:20 | 18 s | **WHAT CAN HOME CIRCUIT BUILD?** → 7 capabilities, 2 s each (one bar at 120 BPM) |
| 07_BRAND_MESSAGE | 1:38 | 15 s | montage, music dip on "แต่มันเริ่มจาก…", back on the hit → **REAL PROBLEMS / ENGINEERING / SOLUTIONS** |
| 08_ENDING | 1:53 | 7 s | temporary logo, HARDWARE • IoT • GATEWAY • ROBOTICS, **HAVE AN IDEA? LET'S BUILD IT.**, power-down + relay click |

## Editing guide

- **Scene or shot durations:** edit the shot table at the top of each `src/scenes/sNN_*.py`
  (`SHOTS`, `D`, `STAGES`, `ITEM`…). Global start times, VO placement,
  subtitles, SFX and music sections all shift with it. Then run
  `python3 -m src.render --scenes NN`.
- **On-screen text:** `Line("TEXT", font_key, size, color, tracking)` inside each scene's `build()`.
- **VO lines and subtitles:** each `VO(...)` holds the Thai text, the subtitle line
  breaks (maximum two lines per event), the scratch TTS text and the slot length.
- **Replace the voice:** record the lines in `audio/voiceover/VO_SCRIPT.md`, save them as
  `audio/voiceover/vo01.wav …` (16-bit WAV), empty `audio/voiceover/_scratch.json`, and run
  `python3 -m src.render --audio-only`. Subtitle timing follows the real durations.
- **Replace pictures:** put a photo or AI still (16:9, at least 2304×1296) at
  `assets/images/<plate>__bg.png` and delete that plate's `__mid/__fx/__fg.png`.
  Camera moves and overlays keep working. Plate names are listed in `src/plates.py`.
  Animated screen content (code, scope traces, LEDs) is positioned by
  constants in `src/plates.py` and may need a nudge.
- **Replace products:** overwrite `assets/products/*.png` (transparent PNG, same size).
- **Replace the logo:** overwrite `assets/logo/hc_logo_mark.png` and set
  `USE_LOGO_PNG = True` in `src/engine/logo.py`.
- **Replace the music:** put the track at `audio/music/music_score.wav` and render with `--keep-music`.
- **Replace SFX:** drop a WAV with the same name into `audio/sfx/`.
- **Look:** palette, grain, vignette and encoding are set in `src/config.py`. Grades
  (`warm`, `tech`, `neutral`, `cool`) are set per shot.

## Future 9:16 version

Key subjects, headlines, labels and subtitles are kept in the centre of
the frame. The central 608 px column (`config.SAFE_9x16_X0..X1`) holds each
shot's subject. Plates are 2304×1296 with extra margin, so a vertical cut can
reframe with the same camera system and a vertical output size.

## What is temporary in this draft

| Element | Status |
|---|---|
| All imagery (workshop, people, projects, drone, farm, classroom…) | Procedural illustrated **concept plates**, not real footage |
| HC GW-01 gateway, PROTO-02, HC-DEV boards | **Conceptual products**, marked `DRAFT VISUAL` on screen. Not real products |
| Logo | **Temporary** concept (house outline + PCB trace) |
| Thai voice-over | **Scratch TTS** (espeak-ng, robotic). Neural Thai TTS was not reachable from the build environment. Timing is final, voice is not |
| Music | Generated placeholder score (120 BPM, no vocals) |
| SFX | Synthesized placeholders |
| Public-sector / university shots | Generic concepts: no real logos, insignia or named organisations |
| Code, chat messages and CAD screens | Illustrative UI text |

The footer "CONCEPT VISUALIZATION" appears on the end card.

## Fonts & licences

- Inter / Inter Display: SIL OFL 1.1
- Noto Sans Mono: SIL OFL 1.1
- HC Thai Sans: a merge of Noto Sans and Noto Sans Thai, SIL OFL 1.1

All other visual and audio assets are generated by this repository's code.
