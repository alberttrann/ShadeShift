import argparse,json
from pathlib import Path
import geopandas as gpd
import pandas as pd

VALID={"correct","wrong","uncertain"}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",default="labels/gate_b_targeted_visual_review.geojson")
    ap.add_argument("--out",default="logs/gate_b_targeted_visual_review_summary.json")
    args=ap.parse_args()

    g=gpd.read_file(args.input)
    if "visual_verdict" not in g.columns:
        raise SystemExit("Missing visual_verdict field")

    g["visual_verdict"]=g["visual_verdict"].fillna("").astype(str).str.strip().str.lower()
    reviewed=g[g.visual_verdict.isin(VALID)].copy()

    summary={}
    for cat,grp in g.groupby("category"):
        r=reviewed[reviewed.category==cat]
        counts={k:int((r.visual_verdict==k).sum()) for k in ["correct","wrong","uncertain"]}
        summary[str(cat)]={
            "total":int(len(grp)),
            "reviewed":int(len(r)),
            **counts,
            "review_fraction":float(len(r)/len(grp)) if len(grp) else None,
            "correct_fraction_of_reviewed":float(counts["correct"]/len(r)) if len(r) else None,
            "wrong_fraction_of_reviewed":float(counts["wrong"]/len(r)) if len(r) else None,
        }

    result={
        "total_points":int(len(g)),
        "reviewed_points":int(len(reviewed)),
        "unreviewed_points":int(len(g)-len(reviewed)),
        "allowed_visual_verdicts":sorted(VALID),
        "by_category":summary,
        "interpretation_rule":{
            "correct":"Imagery supports the predicted stable class/change, or supports unknown as genuinely ambiguous/mixed.",
            "wrong":"Imagery clearly contradicts the prediction.",
            "uncertain":"Available imagery is insufficient or ambiguous."
        },
        "note":"This script summarizes review evidence only; it intentionally does not auto-pass Gate B from arbitrary visual thresholds."
    }

    Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    Path(args.out).write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    main()
