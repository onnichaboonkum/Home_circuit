"""Global timeline: scene order. Each scene module exposes build() -> Scene.

Scene durations are defined at the top of each scene module (shot duration
tables). The global start of every scene is derived here, so changing one
scene's length automatically shifts everything after it (VO, SFX, subtitles,
music marks included).
"""
from importlib import import_module

SCENE_MODULES = [
    "s01_hook",
    "s02_beginning",
    "s03_idea_to_hardware",
    "s04_projects",
    "s05_philosophy",
    "s06_capabilities",
    "s07_brand_message",
    "s08_ending",
]


def load_scenes(only=None):
    scenes = []
    t = 0.0
    for mod in SCENE_MODULES:
        sc = import_module(f"src.scenes.{mod}").build()
        sc.start = t
        t += sc.duration
        scenes.append(sc)
    if only:
        scenes = [s for s in scenes if s.name in only or s.name.split("_")[0] in only]
    return scenes


def total_duration(scenes):
    return sum(s.duration for s in scenes)
