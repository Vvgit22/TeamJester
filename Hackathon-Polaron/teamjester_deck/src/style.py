"""Shared visual style for the TeamJester overview deck (PPTX + figures)."""
import os

# --- colours -----------------------------------------------------------------
NAVY = "1B2A41"        # main text
NAVY2 = "3A4B63"       # secondary text
GREY = "6B7785"        # captions, footers
RULE = "C5CED8"        # hairline rules
PANEL = "F4F6F9"       # light panel fill
TEAL = "1E7B85"        # restrained accent
TEAL_LIGHT = "E4F1F2"
AMBER = "B26B00"       # "tentative" status text
WHITE = "FFFFFF"

# batch colours = main's analysis/common.py BATCH_COLORS (Okabe-Ito)
BATCH = {"Batch_1": "E69F00", "Batch_2": "009E73", "Batch_3": "0072B2"}
BATCH_LIGHT = {"Batch_1": "F5D9A3", "Batch_2": "A6DCC9", "Batch_3": "A9CBE6"}
BATCH_SHORT = {"Batch_1": "Batch 1", "Batch_2": "Batch 2", "Batch_3": "Batch 3"}

# segmentation class colours used in every overlay of this deck
PORE_RGB = (214, 40, 57)        # crimson
BRIGHT_RGB = (242, 194, 48)     # gold
NEAR_RGB = (25, 195, 230)       # cyan: Si boundary within 3 px of a pore
FAR_RGB = (40, 52, 72)          # navy: Si boundary farther from pores


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# --- fonts (Latin Modern, GUST; installed in ~/Library/Fonts) -----------------
TITLE_FONT = "LMRoman17"
HEAD_FONT = "LMRoman12"
BODY_FONT = "LMSans10"
MONO_FONT = "LMMono10"

FONT_FILES = {
    "LMSans10": "lmsans10-regular.otf",
    "LMSans10-Bold": "lmsans10-bold.otf",
    "LMRoman12": "lmroman12-regular.otf",
    "LMRoman17": "lmroman17-regular.otf",
}


def register_mpl_fonts():
    """Make the Latin Modern fonts available to matplotlib (if installed)."""
    from matplotlib import font_manager, rcParams
    fdir = os.path.expanduser("~/Library/Fonts")
    for fn in FONT_FILES.values():
        p = os.path.join(fdir, fn)
        if os.path.exists(p):
            font_manager.fontManager.addfont(p)
    rcParams["font.family"] = "LMSans10"
    rcParams["mathtext.fontset"] = "cm"
    rcParams["axes.edgecolor"] = "#" + NAVY2
    rcParams["axes.labelcolor"] = "#" + NAVY
    rcParams["xtick.color"] = "#" + NAVY2
    rcParams["ytick.color"] = "#" + NAVY2
    rcParams["text.color"] = "#" + NAVY
