"""Stale-number and archived-route check for the clean deliverables.

Fails (exit 1) if any forbidden stale value or archived route is
referenced in the generated paper or reports. Run after build_paper.py.
"""
from __future__ import annotations

import re
import sys

PAPER = "paper/micro2dfn_paper.tex"

# forbidden stale strings/values from superseded runs or archived claims
FORBIDDEN = [
    "4313", "1714",                     # old object counts
    "14.3", "81.8",                    # old buggy DFN numbers
    "vertical texture is material",
    "fft_vh",
    "tau_fdm", "pore_spans",
    "9.5--10.0", "0.095 & 0.098",       # old marker table
    "9-point", "27 solves", "3 cycles",
    "1.555",                            # old t_core
    "more clustered than Batch",
    "excess silicon",
    "process variation, not formula",
    "artefact budget",
    "Si more clumped",
    "fig_si_positions", "fig_deficit_map",
    "immune to the confound",
    "every Batch\\_1 photo has",
    "calendering texture",
]

ARCHIVED_ROUTES = ["recon3d/", "orientation_features",
                   "_fdm_tortuosity"]

# archived-route references are allowed when explicitly pointing at the
# archive itself (e.g. archive/recon3d/run_recon3d.py)
def _live_route_refs(text: str, routes) -> list:
    hits = []
    for m in re.finditer(r"recon3d/|orientation_features|_fdm_tortuosity",
                         text):
        ctx = text[max(0, m.start() - 30):m.start()]
        if "archive/" in ctx:
            continue
        hits.append(m.group(0))
    return hits


def _results_traceability() -> list:
    """Every number cited in RESULTS.html/RESULTS.md must be reproducible
    from its declared source file; the HTML must contain no raw markdown
    and all figures must be embedded data URIs. Returns failures."""
    import os

    import pandas as pd
    bad = []
    if not os.path.exists("RESULTS.html"):
        return ["RESULTS.html missing"]
    doc = open("RESULTS.html").read()
    md = open("RESULTS.md").read() if os.path.exists("RESULTS.md") else ""
    f = pd.read_csv("validated_comparison/per_image_features.csv")
    pw = pd.read_csv("validated_comparison/pairwise_comparisons.csv")
    acq = pd.read_csv("image_acquisition.csv")
    bench = pd.read_csv("benchmark_results.csv")
    bl = pd.read_csv("blocked_permutation.csv")
    truth = pd.read_csv("new_batch_ground_truth.csv")
    b3 = f[f.batch == "Batch_3"]

    def req(s, label):
        if str(s) not in doc:
            bad.append(f"RESULTS.html missing {label}={s}")

    # --- HTML hygiene: no raw markdown, all figures embedded ----------
    for tok in ("**", "`", "![", "]("):
        if tok in doc:
            bad.append(f"RESULTS.html contains literal {tok!r}")
    for m in re.finditer(r'<img[^>]*src="([^"]{0,40})', doc):
        if not m.group(1).startswith("data:image/png;base64,"):
            bad.append("RESULTS.html has a non-embedded figure: "
                       + m.group(1))

    # --- traceability: displayed numbers recomputed from CSVs ---------
    req(f"{f[f.batch=='Batch_1'].pore_frac.median()*100:.0f}%", "B1 pore %")
    req(f"{b3.pore_frac.median()*100:.0f}%", "B3 pore %")
    req(f"{b3.si_candidate_frac.median()*100:.0f}%", "B3 Si %")
    mdd_si = pw[(pw.pair == "Batch_1-Batch_3") &
                (pw.feature == "si_candidate_frac")].mdd_critical.iloc[0]
    mdd_pore = pw[(pw.pair == "Batch_1-Batch_3") &
                  (pw.feature == "pore_frac")].mdd_critical.iloc[0]
    req(f"{mdd_si*100:.1f}", "Si detect limit")
    req(f"{mdd_pore*100:.0f}", "pore detect limit")
    unc_b1 = f[f.batch == "Batch_1"].uncertain_bright_frac
    req(f"{unc_b1.max()*100:.0f}%", "B1 unc top")
    req(f"{unc_b1.nlargest(2).iloc[1]*100:.1f}%", "B1 unc second")
    req(f"{b3.uncertain_bright_frac.max()*100:.1f}%", "B3 unc max")
    req(str(acq.group_id.nunique()), "n sessions")
    req(f"{int((acq.raw_p1 == 0).sum())}/{len(acq)}", "clipped count")
    loo = bench[bench.protocol == "LOO"].set_index("method")
    req(f"{loo.loc['acq_signature','accuracy']*100:.0f}%", "acq LOO %")
    req(f"{loo.loc['envelope','accuracy']*100:.0f}%", "envelope LOO %")
    sh = {r.pair: int(r.n_pair_groups)
          for r in bl[bl.marker == "pore_frac"].itertuples()}
    req(str(sh.get("Batch_1-Batch_3")), "B1-B3 shared groups")
    # confirmed labels in the blind-call table match the truth file
    for r in truth.itertuples():
        if r.confirmed_label.replace("_", " ") not in doc:
            bad.append(f"RESULTS.html missing truth {r.image_id}")
    # withdrawn-claim scan on both deliverables
    for name, text in (("RESULTS.html", doc), ("RESULTS.md", md)):
        for s in FORBIDDEN:
            if s in text:
                bad.append(f"{name}: {s}")
        for s in _live_route_refs(text, ARCHIVED_ROUTES):
            bad.append(f"{name}: {s}")
    return bad


def main() -> int:
    tex = open(PAPER).read()
    bad = []
    for s in FORBIDDEN:
        if s in tex:
            bad.append(s)
    bad += _live_route_refs(tex, ARCHIVED_ROUTES)
    # same stale-pattern guard on the other deliverables
    for path in ("dfn_output/report.md", "channel_report.md",
                 "spatial_report.md", "MEASUREMENT_FOUNDATION.md",
                 "orientation_analysis/orientation_report.md"):
        try:
            doc = open(path).read()
        except FileNotFoundError:
            continue
        # AUDIT_LEDGER.md legitimately names removed routes (it is the
        # evidence trail); scan it for live-route references only.
        if "AUDIT_LEDGER" not in path:
            for s in FORBIDDEN:
                if s in doc:
                    bad.append(f"{path}: {s}")
        for s in _live_route_refs(doc, ARCHIVED_ROUTES):
            bad.append(f"{path}: {s}")
    # hand-typed-number guard: key values must match report_numbers
    import json
    n = json.load(open("report_numbers.json"))
    med = n["fractions"]["si_candidate_frac"]
    for b, v in med.items():
        pct = f"{v['med'] * 100:.1f}"
        if pct not in tex:
            bad.append(f"missing Si frac {b}={pct}")
    pf = n["fractions"]["pore_frac"]
    for b, v in pf.items():
        pct = f"{v['med'] * 100:.1f}"
        if pct not in tex:
            bad.append(f"missing pore frac {b}={pct}")
    bad += _results_traceability()
    if bad:
        print("STALE/FORBIDDEN content found:")
        for s in bad:
            print("  -", s)
        return 1
    print("check_report: clean — no stale numbers or archived routes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
