import argparse, json, math
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import geometry_mask
from shapely.geometry import box, mapping

MODERATE_NAMES=["jan19","feb04","feb28","mar24","apr25","apr09_partial","apr17_partial"]
MODERATE_CORE=["jan19","feb04","feb28","mar24","apr25"]
GUARDED_NAMES=["jan19","feb04","feb28","mar24"]

def read(path):
    with rasterio.open(path) as ds:
        return ds.read(), ds.transform, ds.crs, ds.bounds

def values(arr, transform, geom, band):
    mask=geometry_mask([mapping(geom)], out_shape=arr.shape[1:], transform=transform, invert=True)
    return arr[band][mask]

def scene_cell_medians(arr, transform, polys, names, min_cov):
    med={name:[] for name in names}
    cov={name:[] for name in names}
    for geom in polys:
        for i,name in enumerate(names):
            v=values(arr,transform,geom,i).astype(float)
            valid=np.isfinite(v) & (v>-9990)
            coverage=float(valid.mean()) if v.size else 0.0
            cov[name].append(coverage)
            med[name].append(
                float(np.median(v[valid]))
                if coverage>=min_cov and valid.any()
                else np.nan
            )
    return pd.DataFrame(med), pd.DataFrame({f"{k}_coverage":v for k,v in cov.items()})

def percentile_columns(df, cols, spatial_ok):
    """
    Rank only spatially valid planning cells.
    This prevents tiny boundary slivers from entering the AOI percentile
    distribution and receiving extreme heat percentiles.
    """
    out=pd.DataFrame(index=df.index)
    spatial_ok=np.asarray(spatial_ok,dtype=bool)
    for c in cols:
        out[f"{c}_pct"]=np.nan
        ok=df[c].notna().to_numpy() & spatial_ok
        if ok.any():
            s=df.loc[ok,c]
            out.loc[ok,f"{c}_pct"]=s.rank(method="average",pct=True)
    return out

def finite_iqr(values):
    a=np.asarray(values,dtype=float)
    a=a[np.isfinite(a)]
    if len(a)==0:
        return np.nan
    return float(np.quantile(a,.75)-np.quantile(a,.25))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--config",default="config/gate_c4_config.json")
    ap.add_argument("--landcover",default="outputs/reliable_landcover_2025.tif")
    ap.add_argument("--change",default="outputs/reliable_change_code_2017_2025.tif")
    ap.add_argument("--moderate",default="data/shadeshift_gate_c3_landsat_moderate_anomalies.tif")
    ap.add_argument("--guarded",default="data/shadeshift_gate_c3_landsat_guarded_anomalies.tif")
    ap.add_argument("--out",default="public/data/planning_cells.geojson")
    ap.add_argument("--top",default="public/data/priority_top10.json")
    ap.add_argument("--summary",default="logs/gate_c4_planning_grid.json")
    args=ap.parse_args()

    cfg=json.loads(Path(args.config).read_text(encoding="utf-8"))
    cell=float(cfg["grid_m"])
    min_scene_cov=float(cfg["thermal"]["min_cell_scene_coverage"])
    min_scene_count=int(cfg["thermal"]["min_moderate_scene_count"])
    hot_thr=float(cfg["thermal"]["hot_percentile_threshold"])
    min_overlap=float(cfg["landcover"]["min_footprint_overlap_fraction"])

    lc,lct,lccrs,bounds=read(args.landcover)
    lc=lc[0]
    ch,cht,chcrs,_=read(args.change)
    ch=ch[0]
    mod,modt,modcrs,_=read(args.moderate)
    grd,grdt,grdcrs,_=read(args.guarded)

    if lccrs is None or lccrs.to_string()!="EPSG:32648":
        raise SystemExit(f"Expected landcover EPSG:32648, got {lccrs}")
    if chcrs!=lccrs or cht!=lct:
        raise SystemExit("Change raster is not aligned with landcover.")
    if modcrs is None or modcrs.to_string()!="EPSG:32648" or mod.shape[0]!=len(MODERATE_NAMES):
        raise SystemExit("Moderate Landsat stack must be 7-band EPSG:32648.")
    if grdcrs is None or grdcrs.to_string()!="EPSG:32648" or grd.shape[0]!=len(GUARDED_NAMES):
        raise SystemExit("Guarded Landsat stack must be 4-band EPSG:32648.")

    raster_extent=box(bounds.left,bounds.bottom,bounds.right,bounds.top)

    # Preserve the stable snapped 500 m grid and existing cell IDs.
    xmin=math.floor(bounds.left/cell)*cell
    ymin=math.floor(bounds.bottom/cell)*cell
    xmax=math.ceil(bounds.right/cell)*cell
    ymax=math.ceil(bounds.top/cell)*cell

    full_polys=[]; clipped_polys=[]; ids=[]; overlap_fracs=[]
    cid=0
    y=ymin
    while y<ymax:
        x=xmin
        while x<xmax:
            geom=box(x,y,x+cell,y+cell)
            if geom.intersects(raster_extent):
                inter=geom.intersection(raster_extent)
                frac=float(inter.area/geom.area) if geom.area else 0.0
                full_polys.append(geom)
                clipped_polys.append(inter)
                overlap_fracs.append(frac)
                ids.append(f"C{cid:03d}")
                cid+=1
            x+=cell
        y+=cell

    # Use full grid cell geometry for sampling but clipped geometry for display/export.
    sampling_polys=full_polys
    spatial_ok=np.asarray(overlap_fracs)>=min_overlap

    g=gpd.GeoDataFrame({
        "cell_id":ids,
        "footprint_overlap_fraction":overlap_fracs,
        "spatial_support_ok":spatial_ok,
    }, geometry=clipped_polys, crs=lccrs)

    # Gate B evidence. The raster mask naturally samples only the actual raster.
    rows=[]
    for geom in sampling_polys:
        v=values(lc[np.newaxis,...],lct,geom,0)
        total=len(v)
        known=np.isin(v,[1,2,4])
        terr=np.isin(v,[1,2])
        known_n=int(known.sum())
        terr_n=int(terr.sum())

        cv=values(ch[np.newaxis,...],cht,geom,0)
        joint=np.isin(cv,[11,12,14,21,22,24,41,42,44])

        rows.append({
            "known_fraction":float(known.mean()) if total else 0.0,
            "terrestrial_share_of_known":float(terr_n/known_n) if known_n else 0.0,
            "vegetation_fraction_terrestrial":float((v==1).sum()/terr_n) if terr_n else np.nan,
            "built_fraction_terrestrial":float((v==2).sum()/terr_n) if terr_n else np.nan,
            "water_fraction_known":float((v==4).sum()/known_n) if known_n else np.nan,
            "historical_v2b_fraction_joint_reliable":float((cv==12).sum()/joint.sum()) if joint.sum() else np.nan,
        })
    land=pd.DataFrame(rows,index=g.index)
    for c in land.columns:
        g[c]=land[c]

    # Landsat scene-wise 500 m medians.
    mod_cells,mod_cov=scene_cell_medians(mod,modt,sampling_polys,MODERATE_NAMES,min_scene_cov)
    grd_cells,grd_cov=scene_cell_medians(grd,grdt,sampling_polys,GUARDED_NAMES,min_scene_cov)

    # CRITICAL FIX: percentile ranks are relative only to spatially supported cells.
    mod_pct=percentile_columns(mod_cells,MODERATE_CORE,spatial_ok)
    grd_pct=percentile_columns(grd_cells,GUARDED_NAMES,spatial_ok)

    for c in mod_cov.columns:
        g[f"thermal_{c}"]=mod_cov[c]
    for c in grd_cov.columns:
        g[f"guarded_{c}"]=grd_cov[c]

    mod_matrix=mod_pct[[f"{x}_pct" for x in MODERATE_CORE]].to_numpy(float)
    grd_matrix=grd_pct[[f"{x}_pct" for x in GUARDED_NAMES]].to_numpy(float)

    mod_count=np.isfinite(mod_matrix).sum(axis=1)
    grd_count=np.isfinite(grd_matrix).sum(axis=1)

    heat=np.full(len(g),np.nan)
    heat_iqr=np.full(len(g),np.nan)
    hot_recurrence=np.full(len(g),np.nan)
    guarded_heat=np.full(len(g),np.nan)

    for i in range(len(g)):
        if not spatial_ok[i]:
            continue

        mv=mod_matrix[i]
        valid=mv[np.isfinite(mv)]
        if len(valid)>=min_scene_count:
            heat[i]=float(np.median(valid))
            heat_iqr[i]=finite_iqr(valid)
            hot_recurrence[i]=float(np.mean(valid>=hot_thr))

        gv=grd_matrix[i]
        gvalid=gv[np.isfinite(gv)]
        if len(gvalid)>=3:
            guarded_heat[i]=float(np.median(gvalid))

    g["heat_score"]=heat
    g["heat_scene_count"]=mod_count
    g["heat_scene_fraction"]=mod_count/len(MODERATE_CORE)
    g["heat_rank_iqr"]=heat_iqr
    g["hot_recurrence"]=hot_recurrence
    g["guarded_heat_score"]=guarded_heat
    g["guarded_scene_count"]=grd_count
    g["qa_tier_heat_gap"]=np.abs(g["heat_score"]-g["guarded_heat_score"])

    # Partial validation percentile ranks also use spatially valid cells only.
    for name in ["apr09_partial","apr17_partial"]:
        g[f"{name}_heat_percentile"]=np.nan
        ok=mod_cells[name].notna().to_numpy() & spatial_ok
        if ok.any():
            g.loc[ok,f"{name}_heat_percentile"]=mod_cells.loc[ok,name].rank(method="average",pct=True)

    g["greening_need"]=g["built_fraction_terrestrial"]
    hw=float(cfg["priority"]["heat_weight"])
    gw=float(cfg["priority"]["greening_need_weight"])
    g["priority_core"]=hw*g["heat_score"]+gw*g["greening_need"]

    g["eligible"]=(
        g["spatial_support_ok"].astype(bool) &
        (g["known_fraction"]>=cfg["landcover"]["min_known_fraction"]) &
        (g["terrestrial_share_of_known"]>=cfg["landcover"]["min_terrestrial_share"]) &
        (g["heat_scene_count"]>=min_scene_count) &
        g["heat_score"].notna() &
        g["greening_need"].notna()
    )

    g["priority_rank"]=np.nan
    if g["eligible"].any():
        g.loc[g["eligible"],"priority_rank"]=(
            g.loc[g["eligible"],"priority_core"].rank(ascending=False,method="min")
        )

    # Keep evidence dimensions transparent.  Edge coverage is now part of support.
    g["evidence_coverage_score"]=np.minimum.reduce([
        g["known_fraction"].to_numpy(float),
        g["heat_scene_fraction"].to_numpy(float),
        g["footprint_overlap_fraction"].to_numpy(float)
    ])

    def explain(r):
        if not bool(r["spatial_support_ok"]):
            return "excluded: less than 50% of the 500m planning cell overlaps the study footprint"
        if not bool(r["eligible"]):
            return "insufficient evidence for ranking"
        parts=[]
        if r["heat_score"]>=0.75:
            parts.append("persistent high daytime thermal rank")
        elif r["heat_score"]>=0.60:
            parts.append("above-average persistent daytime thermal rank")
        if r["greening_need"]>=0.75:
            parts.append("built-dominant / low vegetation")
        elif r["greening_need"]>=0.60:
            parts.append("limited vegetation relative to built cover")
        if pd.notna(r["hot_recurrence"]) and r["hot_recurrence"]>=0.6:
            parts.append("hot-quartile recurrence across dates")
        if pd.notna(r["qa_tier_heat_gap"]) and r["qa_tier_heat_gap"]<=0.10:
            parts.append("moderate/guarded QA agreement")
        if r["footprint_overlap_fraction"]<0.999:
            parts.append("partial edge planning cell")
        if pd.notna(r["historical_v2b_fraction_joint_reliable"]) and r["historical_v2b_fraction_joint_reliable"]>=0.05:
            parts.append("historical vegetation-to-built evidence")
        return "; ".join(parts) if parts else "combined thermal and greening-need evidence"

    g["evidence_reason"]=g.apply(explain,axis=1)

    out=Path(args.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    g.to_crs("EPSG:4326").to_file(out,driver="GeoJSON")

    top=g[g["eligible"]].sort_values(["priority_rank","cell_id"]).head(10)
    top_records=[]
    for _,r in top.iterrows():
        top_records.append({
            "cell_id":str(r["cell_id"]),
            "priority_rank":int(r["priority_rank"]),
            "priority_core":float(r["priority_core"]),
            "heat_score":float(r["heat_score"]),
            "greening_need":float(r["greening_need"]),
            "heat_scene_count":int(r["heat_scene_count"]),
            "hot_recurrence":float(r["hot_recurrence"]) if pd.notna(r["hot_recurrence"]) else None,
            "heat_rank_iqr":float(r["heat_rank_iqr"]) if pd.notna(r["heat_rank_iqr"]) else None,
            "guarded_heat_score":float(r["guarded_heat_score"]) if pd.notna(r["guarded_heat_score"]) else None,
            "qa_tier_heat_gap":float(r["qa_tier_heat_gap"]) if pd.notna(r["qa_tier_heat_gap"]) else None,
            "vegetation_fraction_terrestrial":float(r["vegetation_fraction_terrestrial"]),
            "built_fraction_terrestrial":float(r["built_fraction_terrestrial"]),
            "historical_v2b_fraction_joint_reliable":float(r["historical_v2b_fraction_joint_reliable"]) if pd.notna(r["historical_v2b_fraction_joint_reliable"]) else None,
            "footprint_overlap_fraction":float(r["footprint_overlap_fraction"]),
            "evidence_coverage_score":float(r["evidence_coverage_score"]),
            "evidence_reason":str(r["evidence_reason"]),
        })
    Path(args.top).parent.mkdir(parents=True,exist_ok=True)
    Path(args.top).write_text(json.dumps(top_records,indent=2),encoding="utf-8")

    overlap_counts={
        "lt_0_5":int((g["footprint_overlap_fraction"]<0.5).sum()),
        "ge_0_5":int((g["footprint_overlap_fraction"]>=0.5).sum()),
        "full":int(np.isclose(g["footprint_overlap_fraction"],1.0).sum())
    }

    summary={
        "revision":"C4-v3-spatial-fix",
        "grid_m":cell,
        "cells_total":int(len(g)),
        "cells_spatially_supported":int(g["spatial_support_ok"].sum()),
        "cells_eligible":int(g["eligible"].sum()),
        "min_footprint_overlap_fraction":min_overlap,
        "overlap_counts":overlap_counts,
        "thermal_consensus":"median of per-date 500m within-AOI percentile ranks, ranked only over spatially supported cells",
        "moderate_core_scene_count":len(MODERATE_CORE),
        "guarded_core_scene_count":len(GUARDED_NAMES),
        "priority_formula":f"{hw:.2f}*heat_score + {gw:.2f}*greening_need",
        "historical_change_in_core_score":False,
        "qa_tier_gap_median_eligible":(
            float(g.loc[g["eligible"],"qa_tier_heat_gap"].median(skipna=True))
            if g["eligible"].any() else None
        ),
        "outputs":{"geojson":args.out,"top10":args.top}
    }
    Path(args.summary).parent.mkdir(parents=True,exist_ok=True)
    Path(args.summary).write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps(summary,indent=2))

if __name__=="__main__":
    main()
