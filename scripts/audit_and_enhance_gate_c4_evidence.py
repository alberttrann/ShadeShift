import argparse, json
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import geometry_mask
from shapely.geometry import mapping

MODERATE_NAMES=[
    "jan19","feb04","feb28","mar24","apr25",
    "apr09_partial","apr17_partial"
]
MODERATE_CORE=["jan19","feb04","feb28","mar24","apr25"]
GUARDED_NAMES=["jan19","feb04","feb28","mar24"]
SHARED_DATES=["jan19","feb04","feb28","mar24"]
PARTIAL_DATES=["apr09_partial","apr17_partial"]

def read_stack(path, expected_bands):
    with rasterio.open(path) as ds:
        if ds.count != expected_bands:
            raise SystemExit(
                f"{path}: expected {expected_bands} bands, found {ds.count}"
            )
        if ds.crs is None or ds.crs.to_string()!="EPSG:32648":
            raise SystemExit(f"{path}: expected EPSG:32648, found {ds.crs}")
        return ds.read().astype("float32"), ds.transform, ds.crs

def cell_values(arr, transform, geom, band):
    mask=geometry_mask(
        [mapping(geom)],
        out_shape=arr.shape[1:],
        transform=transform,
        invert=True
    )
    return arr[band][mask].astype(float)

def aggregate_scene_cells(arr, transform, g, names, min_cov):
    med=pd.DataFrame(index=g.index)
    cov=pd.DataFrame(index=g.index)
    for i,name in enumerate(names):
        vals=[]
        cover=[]
        for geom in g.geometry:
            v=cell_values(arr,transform,geom,i)
            valid=np.isfinite(v) & (v>-9990)
            c=float(valid.mean()) if v.size else 0.0
            cover.append(c)
            vals.append(
                float(np.median(v[valid]))
                if c>=min_cov and valid.any()
                else np.nan
            )
        med[name]=vals
        cov[name]=cover
    return med,cov

def percentile_rank(df, names, spatial_ok):
    out=pd.DataFrame(index=df.index)
    spatial_ok=np.asarray(spatial_ok,dtype=bool)
    for name in names:
        out[name]=np.nan
        ok=df[name].notna().to_numpy() & spatial_ok
        if ok.any():
            out.loc[ok,name]=df.loc[ok,name].rank(
                method="average",
                pct=True
            )
    return out

def finite_median(a):
    a=np.asarray(a,dtype=float)
    a=a[np.isfinite(a)]
    return float(np.median(a)) if len(a) else np.nan

def loo_range(a):
    a=np.asarray(a,dtype=float)
    a=a[np.isfinite(a)]
    if len(a)<3:
        return np.nan
    meds=[]
    for i in range(len(a)):
        b=np.delete(a,i)
        if len(b)>=2:
            meds.append(float(np.median(b)))
    return float(max(meds)-min(meds)) if meds else np.nan

def classify_temporal(n, loo):
    if n>=4 and np.isfinite(loo) and loo<=0.10:
        return "strong"
    if n>=3 and np.isfinite(loo) and loo<=0.20:
        return "moderate"
    return "limited"

def classify_qa(n, gap):
    if n>=3 and np.isfinite(gap) and gap<=0.05:
        return "strong"
    if n>=3 and np.isfinite(gap) and gap<=0.10:
        return "moderate"
    if n<3:
        return "insufficient"
    return "discordant"

def classify_spatial(overlap):
    if overlap>=0.99:
        return "full"
    if overlap>=0.75:
        return "strong_partial"
    if overlap>=0.50:
        return "minimum_supported"
    return "unsupported"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument(
        "--grid",
        default="public/data/planning_cells.geojson"
    )
    ap.add_argument(
        "--moderate",
        default="data/shadeshift_gate_c3_landsat_moderate_anomalies.tif"
    )
    ap.add_argument(
        "--guarded",
        default="data/shadeshift_gate_c3_landsat_guarded_anomalies.tif"
    )
    ap.add_argument("--min-cell-coverage",type=float,default=0.50)
    ap.add_argument(
        "--out-grid",
        default="public/data/planning_cells_evidence_enhanced.geojson"
    )
    ap.add_argument(
        "--out-top",
        default="public/data/priority_top10_evidence_enhanced.json"
    )
    ap.add_argument(
        "--out-strong",
        default="public/data/high_confidence_priority_top10.json"
    )
    ap.add_argument(
        "--out-audit",
        default="logs/gate_c4_1_caveat_audit.json"
    )
    args=ap.parse_args()

    g=gpd.read_file(args.grid)
    if g.crs is None:
        raise SystemExit("Planning GeoJSON has no CRS.")
    g=g.to_crs("EPSG:32648")

    mod,modt,_=read_stack(args.moderate,len(MODERATE_NAMES))
    grd,grdt,_=read_stack(args.guarded,len(GUARDED_NAMES))

    spatial_ok=g["spatial_support_ok"].astype(bool).to_numpy()

    mod_med,mod_cov=aggregate_scene_cells(
        mod,modt,g,MODERATE_NAMES,args.min_cell_coverage
    )
    grd_med,grd_cov=aggregate_scene_cells(
        grd,grdt,g,GUARDED_NAMES,args.min_cell_coverage
    )

    mod_pct=percentile_rank(mod_med,MODERATE_NAMES,spatial_ok)
    grd_pct=percentile_rank(grd_med,GUARDED_NAMES,spatial_ok)

    # ------------------------------------------------------------------
    # 1. Local temporal stability.
    # ------------------------------------------------------------------
    local_core=np.full(len(g),np.nan)
    loo=np.full(len(g),np.nan)
    observed=np.zeros(len(g),dtype=int)

    for i in range(len(g)):
        vals=mod_pct.loc[i,MODERATE_CORE].to_numpy(float)
        vals=vals[np.isfinite(vals)]
        observed[i]=len(vals)
        if len(vals)>=3:
            local_core[i]=float(np.median(vals))
            loo[i]=loo_range(vals)

    g["audit_core_heat_score"]=local_core
    g["audit_core_scene_count"]=observed
    g["heat_loo_median_range"]=loo

    # Difference should be tiny; this is an audit, not a new score.
    g["heat_score_reproduction_gap"]=np.abs(
        g["heat_score"].astype(float)-g["audit_core_heat_score"]
    )

    # ------------------------------------------------------------------
    # 2. PAIRED QA comparison on exactly the same dates/pixels-supported
    #    cells, avoiding the old 5-date-vs-4-date confound.
    # ------------------------------------------------------------------
    paired_count=np.zeros(len(g),dtype=int)
    paired_mod=np.full(len(g),np.nan)
    paired_grd=np.full(len(g),np.nan)
    paired_gap=np.full(len(g),np.nan)
    paired_date_gap_median=np.full(len(g),np.nan)
    paired_date_gap_max=np.full(len(g),np.nan)

    for i in range(len(g)):
        m=[]; q=[]; date_gaps=[]
        for d in SHARED_DATES:
            mv=mod_pct.loc[i,d]
            gv=grd_pct.loc[i,d]
            if np.isfinite(mv) and np.isfinite(gv):
                m.append(float(mv))
                q.append(float(gv))
                date_gaps.append(abs(float(mv)-float(gv)))
        paired_count[i]=len(m)
        if len(m)>=3:
            paired_mod[i]=float(np.median(m))
            paired_grd[i]=float(np.median(q))
            paired_gap[i]=abs(paired_mod[i]-paired_grd[i])
            paired_date_gap_median[i]=float(np.median(date_gaps))
            paired_date_gap_max[i]=float(np.max(date_gaps))

    g["paired_qa_scene_count"]=paired_count
    g["paired_moderate_heat_score"]=paired_mod
    g["paired_guarded_heat_score"]=paired_grd
    g["paired_qa_consensus_gap"]=paired_gap
    g["paired_qa_date_gap_median"]=paired_date_gap_median
    g["paired_qa_date_gap_max"]=paired_date_gap_max

    # ------------------------------------------------------------------
    # 3. Independent partial-date corroboration.
    #    These dates were selected as partial validations before C3 result.
    # ------------------------------------------------------------------
    val_count=np.zeros(len(g),dtype=int)
    val_gap=np.full(len(g),np.nan)
    val_max_gap=np.full(len(g),np.nan)
    val_labels=[]

    for i in range(len(g)):
        gaps=[]
        labels=[]
        core=g.loc[i,"heat_score"]
        if np.isfinite(core):
            for d in PARTIAL_DATES:
                v=mod_pct.loc[i,d]
                if np.isfinite(v):
                    gaps.append(abs(float(v)-float(core)))
                    labels.append(d)
        val_count[i]=len(gaps)
        if gaps:
            val_gap[i]=float(np.median(gaps))
            val_max_gap[i]=float(np.max(gaps))
        val_labels.append(",".join(labels))

    g["partial_validation_count"]=val_count
    g["partial_validation_median_gap"]=val_gap
    g["partial_validation_max_gap"]=val_max_gap
    g["partial_validation_dates"]=val_labels

    # ------------------------------------------------------------------
    # 4. Evidence axes + product-facing grade.
    #
    # These grades DO NOT alter priority_core or priority_rank.
    # They are transparent evidence-strength labels.
    # ------------------------------------------------------------------
    temporal=[]
    qa=[]
    spatial=[]
    grade=[]
    caveats=[]

    for _,r in g.iterrows():
        t=classify_temporal(
            int(r["heat_scene_count"]),
            float(r["heat_loo_median_range"])
            if pd.notna(r["heat_loo_median_range"]) else np.nan
        )
        q=classify_qa(
            int(r["paired_qa_scene_count"]),
            float(r["paired_qa_consensus_gap"])
            if pd.notna(r["paired_qa_consensus_gap"]) else np.nan
        )
        s=classify_spatial(float(r["footprint_overlap_fraction"]))

        temporal.append(t); qa.append(q); spatial.append(s)

        cs=[]
        if int(r["heat_scene_count"])<4:
            cs.append("limited_core_scene_count")
        if q=="insufficient":
            cs.append("insufficient_paired_guarded_support")
        elif q=="discordant":
            cs.append("paired_qa_disagreement")
        if float(r["footprint_overlap_fraction"])<0.99:
            cs.append("partial_spatial_footprint")
        if pd.notna(r["heat_loo_median_range"]) and float(r["heat_loo_median_range"])>0.20:
            cs.append("temporal_rank_instability")

        # Product-facing evidence grade, not a scientific probability.
        if not bool(r["eligible"]):
            gr="unranked"
        elif (
            float(r["evidence_coverage_score"])>=0.75
            and int(r["heat_scene_count"])>=4
            and t=="strong"
            and q=="strong"
            and float(r["footprint_overlap_fraction"])>=0.75
        ):
            gr="A"
        elif (
            int(r["heat_scene_count"])>=3
            and t in ("strong","moderate")
            and (
                q in ("strong","moderate")
                or (
                    int(r["partial_validation_count"])>=1
                    and pd.notna(r["partial_validation_median_gap"])
                    and float(r["partial_validation_median_gap"])<=0.10
                )
            )
            and float(r["footprint_overlap_fraction"])>=0.50
        ):
            gr="B"
        else:
            gr="C"

        grade.append(gr)
        caveats.append(",".join(cs))

    g["temporal_evidence_strength"]=temporal
    g["qa_corroboration_strength"]=qa
    g["spatial_evidence_strength"]=spatial
    g["evidence_grade"]=grade
    g["evidence_caveats"]=caveats

    # Strong-evidence rank is an optional FILTERED shortlist.
    # It never replaces priority_rank.
    strong=g[(g["eligible"].astype(bool)) & (g["evidence_grade"]=="A")].copy()
    strong=strong.sort_values(["priority_core","cell_id"],ascending=[False,True])
    strong["high_confidence_priority_rank"]=np.arange(1,len(strong)+1)

    grade_map=g.set_index("cell_id")["evidence_grade"].to_dict()
    g["high_confidence_priority_rank"]=g["cell_id"].map(
        strong.set_index("cell_id")["high_confidence_priority_rank"].to_dict()
    )

    # ------------------------------------------------------------------
    # 5. Outputs
    # ------------------------------------------------------------------
    outg=g.to_crs("EPSG:4326")
    Path(args.out_grid).parent.mkdir(parents=True,exist_ok=True)
    outg.to_file(args.out_grid,driver="GeoJSON")

    top=g[g["eligible"].astype(bool)].sort_values(
        ["priority_rank","cell_id"]
    ).head(10)

    def rec(r):
        return {
            "cell_id":str(r["cell_id"]),
            "priority_rank":int(r["priority_rank"]),
            "priority_core":float(r["priority_core"]),
            "heat_score":float(r["heat_score"]),
            "greening_need":float(r["greening_need"]),
            "evidence_grade":str(r["evidence_grade"]),
            "temporal_evidence_strength":str(r["temporal_evidence_strength"]),
            "qa_corroboration_strength":str(r["qa_corroboration_strength"]),
            "spatial_evidence_strength":str(r["spatial_evidence_strength"]),
            "heat_scene_count":int(r["heat_scene_count"]),
            "heat_loo_median_range":(
                float(r["heat_loo_median_range"])
                if pd.notna(r["heat_loo_median_range"]) else None
            ),
            "paired_qa_scene_count":int(r["paired_qa_scene_count"]),
            "paired_qa_consensus_gap":(
                float(r["paired_qa_consensus_gap"])
                if pd.notna(r["paired_qa_consensus_gap"]) else None
            ),
            "partial_validation_count":int(r["partial_validation_count"]),
            "partial_validation_median_gap":(
                float(r["partial_validation_median_gap"])
                if pd.notna(r["partial_validation_median_gap"]) else None
            ),
            "footprint_overlap_fraction":float(r["footprint_overlap_fraction"]),
            "evidence_coverage_score":float(r["evidence_coverage_score"]),
            "evidence_caveats":str(r["evidence_caveats"]),
            "evidence_reason":str(r["evidence_reason"]),
        }

    Path(args.out_top).write_text(
        json.dumps([rec(r) for _,r in top.iterrows()],indent=2),
        encoding="utf-8"
    )

    Path(args.out_strong).write_text(
        json.dumps([rec(r) | {
            "high_confidence_priority_rank":
                int(r["high_confidence_priority_rank"])
        } for _,r in strong.head(10).iterrows()],indent=2),
        encoding="utf-8"
    )

    # Audit summaries.
    top_ids=set(top["cell_id"].astype(str))
    strong_top_ids=set(strong.head(10)["cell_id"].astype(str))

    audit={
        "status":"CAVEAT_AUDIT_COMPLETE",
        "core_priority_modified":False,
        "core_priority_note":
            "priority_core and priority_rank are preserved; evidence diagnostics are additive.",
        "cells":{
            "total":int(len(g)),
            "eligible":int(g["eligible"].astype(bool).sum()),
            "grade_A":int((g["evidence_grade"]=="A").sum()),
            "grade_B":int((g["evidence_grade"]=="B").sum()),
            "grade_C":int((g["evidence_grade"]=="C").sum()),
        },
        "top10":{
            "grade_counts":top["evidence_grade"].value_counts().to_dict(),
            "caveated_cells":{
                str(r["cell_id"]):str(r["evidence_caveats"])
                for _,r in top.iterrows()
                if str(r["evidence_caveats"])
            }
        },
        "high_confidence_top10":[
            str(x) for x in strong.head(10)["cell_id"].tolist()
        ],
        "high_confidence_overlap_with_priority_top10":
            int(len(top_ids & strong_top_ids)),
        "diagnostic_definitions":{
            "paired_qa":
                "Moderate and guarded comparisons use the same shared dates; this removes the previous date-set confound.",
            "heat_loo_median_range":
                "Range of the cell's median heat percentile when each observed core date is omitted once.",
            "partial_validation":
                "Apr-09/Apr-17 independent partial validation dates; never included in core priority score.",
            "evidence_grade":
                "Product-facing evidence-strength tier only; not a calibrated probability and does not modify priority."
        }
    }

    Path(args.out_audit).parent.mkdir(parents=True,exist_ok=True)
    Path(args.out_audit).write_text(
        json.dumps(audit,indent=2),
        encoding="utf-8"
    )

    print(json.dumps(audit,indent=2))

if __name__=="__main__":
    main()
