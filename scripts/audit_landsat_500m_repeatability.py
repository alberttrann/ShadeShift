import argparse, json, math, itertools
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import from_bounds
from scipy.stats import pearsonr, spearmanr

MODERATE_BANDS = [
    "jan19",
    "feb04",
    "feb28",
    "mar24",
    "apr25",
    "apr09_partial",
    "apr17_partial",
]

MODERATE_CORE = [
    "jan19",
    "feb04",
    "feb28",
    "mar24",
    "apr25",
]

MODERATE_PARTIAL = [
    "apr09_partial",
    "apr17_partial",
]

GUARDED_BANDS = [
    "jan19",
    "feb04",
    "feb28",
    "mar24",
]

def correlation(a,b,kind):
    valid=np.isfinite(a)&np.isfinite(b)
    if valid.sum()<5:
        return None
    if np.nanstd(a[valid])==0 or np.nanstd(b[valid])==0:
        return None
    r=pearsonr(a[valid],b[valid]) if kind=="pearson" else spearmanr(a[valid],b[valid])
    return {
        "n":int(valid.sum()),
        "r":float(r.statistic),
        "p_value":float(r.pvalue),
    }

def aggregate(path,names,grid_m,min_cov):
    with rasterio.open(path) as ds:
        arr=ds.read().astype("float32")
        arr[arr<=-9990]=np.nan
        bounds=ds.bounds
        transform=ds.transform
        crs=ds.crs.to_string() if ds.crs else None

    if len(names)!=arr.shape[0]:
        raise ValueError(f"{path}: expected {len(names)} bands, found {arr.shape[0]}")
    if crs!="EPSG:32648":
        raise ValueError(f"{path}: expected EPSG:32648, found {crs}")

    xmin=math.floor(bounds.left/grid_m)*grid_m
    ymin=math.floor(bounds.bottom/grid_m)*grid_m
    xmax=math.ceil(bounds.right/grid_m)*grid_m
    ymax=math.ceil(bounds.top/grid_m)*grid_m

    rows=[]
    cid=0
    y=ymin
    while y<ymax:
        x=xmin
        while x<xmax:
            win=from_bounds(x,y,x+grid_m,y+grid_m,transform=transform)
            r0=max(0,int(math.floor(win.row_off)))
            c0=max(0,int(math.floor(win.col_off)))
            r1=min(arr.shape[1],int(math.ceil(win.row_off+win.height)))
            c1=min(arr.shape[2],int(math.ceil(win.col_off+win.width)))

            if r1>r0 and c1>c0:
                rec={"cell_id":f"C{cid:03d}"}
                any_valid=False
                for i,name in enumerate(names):
                    v=arr[i,r0:r1,c0:c1]
                    finite=np.isfinite(v)
                    cov=float(finite.mean()) if v.size else 0
                    rec[f"{name}_coverage"]=cov
                    rec[name]=float(np.nanmedian(v)) if cov>=min_cov else np.nan
                    any_valid=any_valid or finite.any()

                if any_valid:
                    rows.append(rec)
                    cid+=1
            x+=grid_m
        y+=grid_m
    return pd.DataFrame(rows)

def pairwise(df,names):
    out={}
    for a,b in itertools.combinations(names,2):
        aa=df[a].to_numpy(float)
        bb=df[b].to_numpy(float)

        valid=np.isfinite(aa)&np.isfinite(bb)
        entry={
            "pearson":correlation(aa,bb,"pearson"),
            "spearman":correlation(aa,bb,"spearman"),
        }

        if valid.sum()>=8:
            qa=np.nanquantile(aa[valid],0.75)
            qb=np.nanquantile(bb[valid],0.75)
            A=set(np.where(valid&(aa>=qa))[0])
            B=set(np.where(valid&(bb>=qb))[0])
            union=A|B
            entry["hot_quartile_jaccard"]=float(len(A&B)/len(union)) if union else None
            entry["hot_quartile_intersection"]=int(len(A&B))
            entry["hot_quartile_union"]=int(len(union))
        else:
            entry["hot_quartile_jaccard"]=None

        out[f"{a}_vs_{b}"]=entry
    return out

def consensus_validation(df,core_names,validation_names):
    core=df[core_names].to_numpy(float)
    counts=np.isfinite(core).sum(axis=1)
    med=np.full(core.shape[0], np.nan, dtype=float)
    usable=counts>=3
    if usable.any():
        med[usable]=np.nanmedian(core[usable],axis=1)

    out={}
    for name in validation_names:
        v=df[name].to_numpy(float)
        out[name]={
            "pearson":correlation(med,v,"pearson"),
            "spearman":correlation(med,v,"spearman")
        }
    return out

def leave_one_out(df,names):
    out={}
    for held in names:
        train=[x for x in names if x!=held]
        mat=df[train].to_numpy(float)
        counts=np.isfinite(mat).sum(axis=1)
        min_count=max(2,len(train)-1)
        med=np.full(mat.shape[0], np.nan, dtype=float)
        usable=counts>=min_count
        if usable.any():
            med[usable]=np.nanmedian(mat[usable],axis=1)

        target=df[held].to_numpy(float)
        out[held]={
            "pearson":correlation(med,target,"pearson"),
            "spearman":correlation(med,target,"spearman")
        }
    return out

def summarize_pairwise(res):
    ps=[v["spearman"]["r"] for v in res.values() if v.get("spearman")]
    pp=[v["pearson"]["r"] for v in res.values() if v.get("pearson")]
    js=[v["hot_quartile_jaccard"] for v in res.values() if v.get("hot_quartile_jaccard") is not None]
    return {
        "pair_count":len(res),
        "mean_spearman":float(np.mean(ps)) if ps else None,
        "median_spearman":float(np.median(ps)) if ps else None,
        "min_spearman":float(np.min(ps)) if ps else None,
        "mean_pearson":float(np.mean(pp)) if pp else None,
        "median_pearson":float(np.median(pp)) if pp else None,
        "mean_hot_quartile_jaccard":float(np.mean(js)) if js else None,
        "min_hot_quartile_jaccard":float(np.min(js)) if js else None,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--moderate",default="data/shadeshift_gate_c3_landsat_moderate_anomalies.tif")
    ap.add_argument("--guarded",default="data/shadeshift_gate_c3_landsat_guarded_anomalies.tif")
    ap.add_argument("--grid-m",type=float,default=500)
    ap.add_argument("--min-cell-coverage",type=float,default=0.50)
    ap.add_argument("--out",default="logs/gate_c3_landsat_500m_repeatability.json")
    ap.add_argument("--cells-out",default="logs/gate_c3_landsat_500m_cells.csv")
    args=ap.parse_args()

    m=aggregate(args.moderate,MODERATE_BANDS,args.grid_m,args.min_cell_coverage)
    g=aggregate(args.guarded,GUARDED_BANDS,args.grid_m,args.min_cell_coverage)

    moderate_pairs=pairwise(m,MODERATE_CORE)
    guarded_pairs=pairwise(g,GUARDED_BANDS)

    report={
        "grid_m":args.grid_m,
        "min_cell_coverage":args.min_cell_coverage,

        "moderate":{
            "core_scenes":MODERATE_CORE,
            "partial_validation_scenes":MODERATE_PARTIAL,
            "cells":int(len(m)),
            "pairwise_core":moderate_pairs,
            "summary":summarize_pairwise(moderate_pairs),
            "leave_one_out_core_consensus":leave_one_out(m,MODERATE_CORE),
            "partial_validation_vs_core_consensus":
                consensus_validation(m,MODERATE_CORE,MODERATE_PARTIAL),
        },

        "guarded":{
            "core_scenes":GUARDED_BANDS,
            "cells":int(len(g)),
            "pairwise_core":guarded_pairs,
            "summary":summarize_pairwise(guarded_pairs),
            "leave_one_out_core_consensus":leave_one_out(g,GUARDED_BANDS),
        },

        "decision_rule":{
            "strong_support":[
                "moderate median pairwise Spearman >= 0.5",
                "guarded median pairwise Spearman >= 0.5",
                "no systematic negative pairwise correlations",
                "LOO consensus validation broadly positive",
                "hot-quartile overlap materially above chance"
            ],
            "moderate_support":[
                "median Spearman roughly 0.3-0.5 across both tiers",
                "LOO consensus mostly positive",
                "hot-cell overlap shows recurring neighborhoods"
            ],
            "reject_core_heat":[
                "pairwise rankings remain near zero/negative",
                "result only works under one QA tier",
                "LOO consensus is unstable or negative",
                "hot-quartile overlap remains near chance"
            ]
        }
    }

    # Do not auto-pass from arbitrary threshold; expose evidence.
    Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    Path(args.out).write_text(json.dumps(report,indent=2),encoding="utf-8")

    # Save both tables with prefixes for inspection.
    mm=m.add_prefix("moderate_")
    gg=g.add_prefix("guarded_")
    mm.to_csv(args.cells_out.replace(".csv","_moderate.csv"),index=False)
    gg.to_csv(args.cells_out.replace(".csv","_guarded.csv"),index=False)

    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
