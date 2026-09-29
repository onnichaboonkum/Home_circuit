"""Thai subtitles (ASS for burn-in with the brand font, SRT as sidecar).

Max two lines per event, bottom-centre, inside a centred 1200 px column.
Line breaks are authored per VO cue (``VO.sub_lines``); multi-event cues are
split over the spoken duration in proportion to their text length.
"""
from .. import config as C

MARGIN_V = 64
MARGIN_LR = 360
FONT_SIZE = 46


def _ts_ass(t):
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _ts_srt(t):
    t = max(0.0, t)
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def events(vo_items):
    evs = []
    for k, it in enumerate(vo_items):
        groups = it["sub_lines"]
        lens = [sum(len(l) for l in g) for g in groups]
        total = sum(lens) or 1
        t = it["start"]
        for g, L in zip(groups, lens):
            d = it["dur"] * L / total
            evs.append([t, t + d, g])
            t += d
    # hold each event a little after speech, never overlapping the next, min 1.0 s on screen
    for i, e in enumerate(evs):
        nxt = evs[i + 1][0] if i + 1 < len(evs) else e[1] + 5
        e[1] = min(max(e[1] + 0.35, e[0] + 1.0), nxt - 0.04)
    return evs


def caption_events(scenes):
    """On-screen story text as timed events (sidecar SRT for accessibility / translation)."""
    return [[sc.start + c.t, sc.start + c.t_out, c.lines[:2]] for sc in scenes for c in sc.captions]


def build(scenes, vo_items):
    C.BUILD.mkdir(parents=True, exist_ok=True)
    evs = events(vo_items) if vo_items else caption_events(scenes)
    ass = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {C.W}", f"PlayResY: {C.H}", "WrapStyle: 2",
        "ScaledBorderAndShadow: yes", "", "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: TH,{C.SUBTITLE_FONT_NAME},{FONT_SIZE},&H00F2F4F2,&H000000FF,&H00101010,&H78000000,0,0,0,0,100,100,0,0,1,2.6,1.2,2,"
        f"{MARGIN_LR},{MARGIN_LR},{MARGIN_V},222",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    srt = []
    for i, (a, b, lines) in enumerate(evs, 1):
        assert len(lines) <= 2, f"subtitle event has more than two lines: {lines}"
        txt = r"\N".join(lines)
        ass.append(f"Dialogue: 0,{_ts_ass(a)},{_ts_ass(b)},TH,,0,0,0,,{{\\fad(120,120)}}{txt}")
        srt += [str(i), f"{_ts_srt(a)} --> {_ts_srt(b)}", *lines, ""]
    ass_p = C.BUILD / "subtitles_th.ass"
    srt_p = C.BUILD / "subtitles_th.srt"
    ass_p.write_text("\n".join(ass) + "\n", encoding="utf-8")
    srt_p.write_text("\n".join(srt), encoding="utf-8")
    return {"ass": ass_p, "srt": srt_p, "vo_items": vo_items}
