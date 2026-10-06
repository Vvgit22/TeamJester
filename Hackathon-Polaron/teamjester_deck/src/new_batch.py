"""Turn the results of the batch that is still being run into the slide-7
row ("New batch") of the deck.

Accepted inputs (pick whichever your run produced):
  1. categorise_results.csv  - written by main's `python categorise.py <folder>`
                               (one level=sample row + one row per image)
  2. webapp JSON             - the response of main's webapp POST /api/analyze
                               (keys: group, images, warnings, ...)
  3. manual JSON             - new_batch_results/new_batch_TEMPLATE.json filled
                               in by hand (free-text observations/status/follow-up)
A manual JSON may also point to (1) or (2) via "categorise_csv"/"webapp_json"
and override any generated text.
"""
import json
import os

import pandas as pd

DEFAULT_STATUS = ("Indicative — group calls are not yet independently "
                  "validated")
DEFAULT_FOLLOW = ("Check every photo against the quality guards; compare the "
                  "call with the expectation recorded before the run")


def _pct(x):
    return f"{100 * float(x):.0f}%"


def _batch(b):
    return str(b).replace("_", " ")


def _drivers(s, k=3):
    items = [t.strip() for t in str(s).split("|") if t.strip()]
    return "; ".join(items[:k])


def from_categorise_csv(path):
    df = pd.read_csv(path)
    smp = df[df.level == "sample"].iloc[0]
    img = df[df.level == "image"]
    n = len(img)
    agree = int((img.most_like == smp.most_like).sum())
    obs = (f"Group of {n} photo{'s' if n != 1 else ''}: "
           f"{smp.call_inout} of the Batch 3 envelope (distance "
           f"{smp.dist:.2f} vs threshold {smp.threshold:.2f}); most like "
           f"{_batch(smp.most_like)} ({_pct(smp.confidence)} share); "
           f"{agree} of {n} photos individually agree. Top drivers: "
           f"{_drivers(smp.top_features)}")
    rows = "\n".join(
        f"  {r.image_id}: {r.call_inout}, most like {_batch(r.most_like)} "
        f"({_pct(r.confidence)}), distance {r.dist:.2f}/{r.threshold:.2f}"
        for r in img.itertuples())
    return dict(n_images=n, observations=obs, call_inout=smp.call_inout,
                most_like=_batch(smp.most_like), source=os.path.abspath(path),
                source_kind="main analysis/categorise.py classify_folder",
                notes=f"Per-photo calls ({os.path.basename(path)}):\n{rows}")


def from_webapp_json(path):
    with open(path) as f:
        j = json.load(f)
    g, ims = j["group"], j.get("images", [])
    n = int(g.get("n_images", len(ims)))
    agree = sum(im.get("most_like") == g["most_like"] for im in ims)
    drv = "; ".join(f"{d.get('plain', d.get('feature'))} (z={d['z']:.2f})"
                    for d in g.get("drivers", [])[:3])
    obs = (f"Group of {n} photo{'s' if n != 1 else ''}: {g['call_inout']} of "
           f"the Batch 3 envelope (distance {g['dist']:.2f} vs threshold "
           f"{g['threshold']:.2f}); most like {_batch(g['most_like'])} "
           f"({_pct(g['confidence'])} share); {agree} of {n} photos "
           f"individually agree. Top drivers: {drv}")
    rows = "\n".join(
        f"  {im.get('image_id')}: {im.get('call_inout')}, most like "
        f"{_batch(im.get('most_like'))} ({_pct(im.get('confidence', 0))})"
        for im in ims)
    warn = "\n".join(f"  warning: {w}" for w in j.get("warnings", []))
    return dict(n_images=n, observations=obs, call_inout=g["call_inout"],
                most_like=_batch(g["most_like"]), source=os.path.abspath(path),
                source_kind="main webapp /api/analyze",
                notes=f"Per-photo calls:\n{rows}\n{warn}".rstrip())


def load(path, name=None):
    """Return the dict used to fill the slide-7 'New batch' row."""
    path = os.path.abspath(path)
    base = {}
    if path.lower().endswith(".csv"):
        res = from_categorise_csv(path)
    else:
        with open(path) as f:
            j = json.load(f)
        if "group" in j and "images" in j:
            res = from_webapp_json(path)
        else:
            base = j
            res = {}
            d = os.path.dirname(path)
            if j.get("categorise_csv"):
                res = from_categorise_csv(os.path.join(d, j["categorise_csv"]))
            elif j.get("webapp_json"):
                res = from_webapp_json(os.path.join(d, j["webapp_json"]))
            res.setdefault("source", path)
            res.setdefault("source_kind", "manual results file")
    out = dict(name="New batch", status=DEFAULT_STATUS,
               follow_up=DEFAULT_FOLLOW, observations="", notes="",
               n_images=None)
    out.update({k: v for k, v in res.items() if v not in (None, "")})
    out.update({k: v for k, v in base.items()
                if k in ("name", "observations", "status", "follow_up",
                         "notes", "n_images") and v not in (None, "")})
    if name:
        out["name"] = name
    if not out["observations"]:
        raise SystemExit(f"{path}: no observations found to insert")
    return out
