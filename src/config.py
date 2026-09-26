"""Global project configuration: format, palette, fonts and paths.

Everything visual/aural that the client may want to tweak globally lives here.
Scene durations live in ``src/timeline.py``.
"""
from pathlib import Path

# ---------------------------------------------------------------- format
W, H = 1920, 1080
FPS = 30
AUDIO_SR = 48000

# Central 9:16 safe column (for a future vertical cut): 1080 * 9/16 = 607.5 px
SAFE_9x16_W = 608
SAFE_9x16_X0 = (W - SAFE_9x16_W) // 2
SAFE_9x16_X1 = SAFE_9x16_X0 + SAFE_9x16_W

# ---------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
IMAGES = ASSETS / "images"
PRODUCTS = ASSETS / "products"
LOGO_DIR = ASSETS / "logo"
GRAPHICS = ASSETS / "graphics"
FOOTAGE = ASSETS / "footage"
FONTS = ASSETS / "fonts"
AUDIO = ROOT / "audio"
MUSIC_DIR = AUDIO / "music"
SFX_DIR = AUDIO / "sfx"
VO_DIR = AUDIO / "voiceover"
OUTPUT = ROOT / "output"
BUILD = OUTPUT / "build"          # intermediate renders (scene clips, mixes)

FINAL_NAME = "home_circuit_company_story_draft.mp4"

# ---------------------------------------------------------------- palette (RGB)
BLACK = (7, 8, 9)
CHARCOAL = (22, 24, 26)
CHARCOAL_2 = (34, 37, 40)
CHARCOAL_3 = (52, 56, 60)
GREY = (128, 134, 138)
LIGHT_GREY = (196, 200, 202)
WHITE = (242, 244, 242)
GREEN = (46, 214, 115)          # Home Circuit accent
GREEN_DIM = (22, 110, 62)
GREEN_DEEP = (10, 48, 30)
WARM = (255, 176, 96)           # lamp light for the origin story
WARM_DEEP = (120, 60, 24)
COPPER = (201, 142, 72)
GOLD = (214, 176, 96)
SKIN = (182, 128, 96)

# ---------------------------------------------------------------- fonts
FONT_FILES = {
    "display_black": FONTS / "InterDisplay-Black.otf",
    "display_bold": FONTS / "InterDisplay-Bold.otf",
    "display_semibold": FONTS / "InterDisplay-SemiBold.otf",
    "display_light": FONTS / "InterDisplay-Light.otf",
    "ui_medium": FONTS / "Inter-Medium.otf",
    "ui_regular": FONTS / "Inter-Regular.otf",
    "ui_semibold": FONTS / "Inter-SemiBold.otf",
    "mono": FONTS / "NotoSansMono-Regular.ttf",
    "mono_light": FONTS / "NotoSansMono-Light.ttf",
    # Noto Sans + Noto Sans Thai merged (scripts/make_fonts.py): Thai + Latin in one face
    "thai": FONTS / "HCThaiSans-Regular.ttf",
    "thai_medium": FONTS / "HCThaiSans-Medium.ttf",
    "thai_semibold": FONTS / "HCThaiSans-SemiBold.ttf",
}
SUBTITLE_FONT_NAME = "HC Thai Sans Medium"

# ---------------------------------------------------------------- finishing
GRAIN_AMOUNT = 5.0        # 0 disables film grain
VIGNETTE_AMOUNT = 0.32
DRAFT_LABEL = "DRAFT VISUAL"

# ---------------------------------------------------------------- encoding
X264_PRESET = "medium"
X264_CRF_SCENES = 16      # intermediate scene clips (high quality)
X264_CRF_FINAL = 20
FINAL_MAXRATE = "5M"      # caps film-grain bitrate so the draft stays shareable (~75 MB)
AUDIO_BITRATE = "192k"
