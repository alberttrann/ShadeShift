import argparse,json
from pathlib import Path

def load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=".")
    args=ap.parse_args()
    r=Path(args.root)

    thermal=load(r/"notes/gate_c3_thermal_validation.json")
    planning=load(r/"logs/gate_c4_planning_grid.json")
    sensitivity=load(r/"logs/gate_c4_priority_sensitivity.json")

    checks={
        "gate_b_reliable_landcover_exists":(r/"outputs/reliable_landcover_2025.tif").exists(),
        "landsat_moderate_stack_exists":(r/"data/shadeshift_gate_c3_landsat_moderate_anomalies.tif").exists(),
        "landsat_guarded_stack_exists":(r/"data/shadeshift_gate_c3_landsat_guarded_anomalies.tif").exists(),
        "thermal_validation_pass":bool(thermal and thermal.get("status")=="PASSED"),
        "planning_grid_exists":(r/"public/data/planning_cells.geojson").exists(),
        "top10_exists":(r/"public/data/priority_top10.json").exists(),
        "eligible_cells_exist":bool(planning and planning.get("cells_eligible",0)>0),
        "sensitivity_audit_exists":bool(sensitivity),
    }

    passed=all(checks.values())
    result={
        "gate":"C",
        "revision":"C4-v3-spatial-fix",
        "status":"PASSED" if passed else "NOT_PASSED_YET",
        "gate_c_pass":passed,
        "checks":checks,
        "thermal_core":"Landsat 8/9 daytime 500m percentile-rank consensus",
        "ecostress_role":"context-only nighttime NASA evidence",
        "priority_semantics":"Relative investigation priority within the frozen pilot AOI, not a calibrated heat-risk probability.",
        "sensitivity_flags":sensitivity.get("robustness_flags") if sensitivity else None,
        "next":"Frontend integration and demo narrative" if passed else "Resolve missing Gate C artifacts"
    }
    (r/"logs").mkdir(parents=True,exist_ok=True)
    (r/"logs/gate_c_status.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))

    if not passed:
        raise SystemExit(3)

if __name__=="__main__":
    main()
