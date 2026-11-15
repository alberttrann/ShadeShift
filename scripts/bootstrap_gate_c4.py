import json
from pathlib import Path

CONFIG = {
    "version": "Gate-C4-v3-spatial-fix",
    "grid_m": 500,
    "landcover": {
        "min_known_fraction": 0.60,
        "min_terrestrial_share": 0.50,
        "min_footprint_overlap_fraction": 0.50
    },
    "thermal": {
        "moderate_core_scene_names": ["jan19", "feb04", "feb28", "mar24", "apr25"],
        "guarded_core_scene_names": ["jan19", "feb04", "feb28", "mar24"],
        "min_cell_scene_coverage": 0.50,
        "min_moderate_scene_count": 3,
        "hot_percentile_threshold": 0.75,
        "consensus": "median of per-scene within-AOI percentile ranks",
        "guarded_role": "corroboration / QA-tier robustness, not a separate weighted heat term"
    },
    "priority": {
        "heat_weight": 0.60,
        "greening_need_weight": 0.40,
        "historical_change_in_core_score": False,
        "note": "Weights are transparent planning heuristics and are sensitivity-audited."
    }
}

THERMAL_VALIDATION = {
    "gate": "C3",
    "status": "PASSED",
    "thermal_source": "Landsat 8/9 Collection 2 Level-2 Surface Temperature",
    "planning_scale_m": 500,
    "moderate": {
        "core_dates": ["2025-01-19","2025-02-04","2025-02-28","2025-03-24","2025-04-25"],
        "pair_count": 10,
        "mean_spearman": 0.6755792471081524,
        "median_spearman": 0.6640188856124821,
        "min_spearman": 0.16217990904726723,
        "mean_pearson": 0.7449371299127945,
        "median_pearson": 0.7569549766508545,
        "mean_hot_quartile_jaccard": 0.39756074230431476,
        "partial_validation_spearman": {
            "2025-04-09": 0.9358295427555202,
            "2025-04-17": 0.8417391304347825
        },
        "leave_one_out_spearman": {
            "2025-01-19": 0.6737622468766852,
            "2025-02-04": 0.9315617531219569,
            "2025-02-28": 0.9052176727105395,
            "2025-03-24": 0.8882527126045173,
            "2025-04-25": 0.6260022214940406
        }
    },
    "guarded": {
        "core_dates": ["2025-01-19","2025-02-04","2025-02-28","2025-03-24"],
        "pair_count": 6,
        "mean_spearman": 0.7814982167241932,
        "median_spearman": 0.7929699508101992,
        "min_spearman": 0.5766519533566111,
        "mean_pearson": 0.8035640291281613,
        "median_pearson": 0.807440659256548,
        "mean_hot_quartile_jaccard": 0.497314553351705
    },
    "decision": "Landsat daytime thermal consensus promoted to core planning evidence; ECOSTRESS context-only."
}

FRONTEND_CONTRACT = {
    "artifact": "public/data/planning_cells.geojson",
    "priority_semantics": "Relative investigation priority within the frozen pilot AOI; not a calibrated heat-risk probability.",
    "fields": {
        "priority_rank": "1 = investigate first among eligible cells",
        "priority_core": "transparent 0.60*heat_score + 0.40*greening_need heuristic",
        "heat_score": "median percentile rank across validated Landsat daytime dates",
        "greening_need": "built fraction among reliable terrestrial built+vegetation pixels",
        "heat_scene_count": "number of moderate core dates supporting this cell",
        "hot_recurrence": "fraction of supported dates where cell is in hottest quartile",
        "heat_rank_iqr": "temporal dispersion of heat percentile rank",
        "guarded_heat_score": "stricter-QA thermal consensus",
        "qa_tier_heat_gap": "absolute moderate-vs-guarded consensus difference",
        "historical_v2b_fraction_joint_reliable": "supporting evidence only",
        "evidence_reason": "human-readable rationale"
    }
}

def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

def main():
    for d in ["config","notes","logs","public/data"]:
        Path(d).mkdir(parents=True, exist_ok=True)

    # Deterministic frozen C4 provenance/config: overwrite stale or missing copies.
    write_json("config/gate_c4_config.json", CONFIG)
    write_json("notes/gate_c3_thermal_validation.json", THERMAL_VALIDATION)
    write_json("public/data/frontend_contract.json", FRONTEND_CONTRACT)

    print(json.dumps({
        "bootstrap": "PASS",
        "written": [
            "config/gate_c4_config.json",
            "notes/gate_c3_thermal_validation.json",
            "public/data/frontend_contract.json"
        ],
        "config_version": CONFIG["version"],
        "thermal_validation_status": THERMAL_VALIDATION["status"]
    }, indent=2))

if __name__ == "__main__":
    main()
