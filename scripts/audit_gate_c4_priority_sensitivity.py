import argparse,json
from pathlib import Path
import numpy as np
import geopandas as gpd
from scipy.stats import spearmanr

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--grid",default="public/data/planning_cells.geojson")
    ap.add_argument("--out",default="logs/gate_c4_priority_sensitivity.json")
    args=ap.parse_args()

    g=gpd.read_file(args.grid)
    if "eligible" not in g.columns:
        raise SystemExit("planning_cells.geojson is missing 'eligible'")
    g=g[g["eligible"].astype(bool) & g["spatial_support_ok"].astype(bool)].copy()

    if len(g)<5:
        raise SystemExit("Too few eligible cells for sensitivity analysis.")

    scenarios={
        "heat_heavy":(0.70,0.30),
        "baseline":(0.60,0.40),
        "balanced":(0.50,0.50),
        "greening_heavy":(0.40,0.60),
    }

    ranks={}
    tops={}
    scores={}
    n_top=min(10,len(g))

    for name,(hw,gw) in scenarios.items():
        score=hw*g["heat_score"]+gw*g["greening_need"]
        rank=score.rank(ascending=False,method="average")
        ranks[name]=rank
        scores[name]=score
        tops[name]=set(g.loc[rank.nsmallest(n_top).index,"cell_id"].astype(str))

    base=ranks["baseline"]
    result={"eligible_cells":int(len(g)),"top_n":n_top,"scenarios":{}}

    for name,r in ranks.items():
        rho=float(spearmanr(base,r).statistic)
        overlap=float(len(tops["baseline"] & tops[name])/max(1,n_top))
        result["scenarios"][name]={
            "spearman_vs_baseline":rho,
            "top_overlap_vs_baseline":overlap,
        }

    q=g[["heat_score","guarded_heat_score"]].dropna()
    result["qa_tier"]={}
    if len(q)>=5:
        result["qa_tier"]={
            "n":int(len(q)),
            "heat_score_spearman":float(spearmanr(q["heat_score"],q["guarded_heat_score"]).statistic),
            "median_absolute_heat_gap":float(np.median(np.abs(q["heat_score"]-q["guarded_heat_score"]))),
        }

    rhos=[v["spearman_vs_baseline"] for v in result["scenarios"].values()]
    overlaps=[v["top_overlap_vs_baseline"] for v in result["scenarios"].values()]
    qa_rho=result["qa_tier"].get("heat_score_spearman")

    result["robustness_flags"]={
        "all_weight_spearman_ge_0_85":bool(min(rhos)>=0.85),
        "all_top_overlap_ge_0_70":bool(min(overlaps)>=0.70),
        "qa_tier_heat_spearman_ge_0_80":bool(qa_rho>=0.80) if qa_rho is not None else None,
    }
    result["note"]="These are planning robustness diagnostics, not universal scientific thresholds."

    Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    Path(args.out).write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    main()
