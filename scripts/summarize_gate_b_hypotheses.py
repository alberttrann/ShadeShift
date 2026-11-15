import argparse,json
from pathlib import Path

FILES={
 "repeated_group_holdout":"logs/gate_b_repeated_group_holdout.json",
 "label_permutation":"logs/gate_b_label_permutation_test.json",
 "oof_calibration":"logs/gate_b_oof_calibration.json",
 "embedding_support":"logs/gate_b_embedding_support.json",
 "quadrant_holdout":"logs/gate_b_quadrant_holdout.json",
 "spatial_cv":"logs/gate_b_spatial_cv.json",
 "transition":"logs/gate_b_transition_audit.json",
}

def load(p):
    try:return json.loads(Path(p).read_text(encoding="utf-8"))
    except:return None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",default="logs/gate_b_hypothesis_resolution_summary.json")
    args=ap.parse_args()
    data={k:load(v) for k,v in FILES.items()}

    checks={}
    rep=data["repeated_group_holdout"]
    if rep:
        lg=rep["models"]["logistic"]
        checks["robust_repeated_group_holdout"]=bool(lg["mean_macro_f1"]>=0.80 and lg["p05_macro_f1"]>=0.65)

    perm=data["label_permutation"]
    if perm:
        checks["signal_above_null"]=bool(
            perm["empirical_p_value"]<=0.05 and
            perm["observed_grouped_cv_macro_f1"]>perm["null_p95_macro_f1"]
        )

    cal=data["oof_calibration"]
    if cal:
        checks["calibration_not_catastrophic"]=bool(cal["ece_10bin"]<=0.20)

    sup=data["embedding_support"]
    if sup:
        checks["map_embedding_support_reasonable"]=bool(sup["map_2025_supported_fraction"]>=0.80)

    sp=data["spatial_cv"]
    if sp:
        checks["fivefold_group_cv_reasonable"]=bool(sp["models"]["logistic"]["mean_macro_f1"]>=0.80)

    tr=data["transition"]
    if tr:
        checks["transition_audit_exists"]=True

    result={
        "checks":checks,
        "all_computed_checks_pass":bool(checks and all(checks.values())),
        "important_note":"Automated checks do not replace the targeted visual review of full maps and high-confidence transition patches.",
        "raw":data
    }
    Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    Path(args.out).write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps({"checks":checks,"all_computed_checks_pass":result["all_computed_checks_pass"]},indent=2))

if __name__=="__main__":
    main()
