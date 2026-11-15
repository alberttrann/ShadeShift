import argparse,json
from pathlib import Path
import numpy as np,pandas as pd,rasterio,joblib
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.neighbors import NearestNeighbors

FEATURES=[f"f{i:02d}" for i in range(64)]

def apply_support(raster_path, scaler, pca, nn, threshold, out_mask):
    with rasterio.open(raster_path) as ds:
        arr=ds.read().astype("float32")
        valid=np.isfinite(arr).all(axis=0)
        X=arr[:,valid].T
        dist=np.empty(len(X),dtype="float32")
        batch=50000
        for st in range(0,len(X),batch):
            en=min(st+batch,len(X))
            P=pca.transform(scaler.transform(X[st:en]))
            dist[st:en]=nn.kneighbors(P,return_distance=True)[0][:,0].astype("float32")

        support=dist<=threshold
        mask=np.full(valid.shape,255,dtype="uint8")
        mask[valid]=np.where(support,1,0).astype("uint8")

        profile=ds.profile.copy()
        profile.update(count=1,dtype="uint8",nodata=255,compress="deflate")
        Path(out_mask).parent.mkdir(parents=True,exist_ok=True)
        with rasterio.open(out_mask,"w",**profile) as out:
            out.write(mask,1)

    return {
        "supported_fraction":float(support.mean()),
        "unsupported_fraction":float((~support).mean()),
        "distance_median":float(np.median(dist)),
        "distance_p95":float(np.quantile(dist,0.95)),
        "distance_max":float(dist.max())
    }

def make_reliable_map(class_tif, conf_tif, support_tif, out_tif, conf_threshold):
    with rasterio.open(class_tif) as a, rasterio.open(conf_tif) as b, rasterio.open(support_tif) as c:
        cls=a.read(1)
        conf=b.read(1)
        sup=c.read(1)
        profile=a.profile.copy()

    valid=(cls!=255)&np.isfinite(conf)&(sup!=255)
    reliable=valid & (conf>=conf_threshold) & (sup==1)

    out=np.full(cls.shape,255,dtype="uint8")
    out[valid]=0
    out[reliable]=cls[reliable]

    profile.update(count=1,dtype="uint8",nodata=255,compress="deflate")
    Path(out_tif).parent.mkdir(parents=True,exist_ok=True)
    with rasterio.open(out_tif,"w",**profile) as dst:
        dst.write(out,1)

    return {
        "reliable_fraction_of_valid":float(reliable.sum()/valid.sum()),
        "unknown_or_unsupported_fraction":float((valid.sum()-reliable.sum())/valid.sum())
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--samples",default="labels/embedding_samples_2025.csv")
    ap.add_argument("--percentile",type=float,default=95.0)
    ap.add_argument("--confidence-threshold",type=float,default=0.60)
    ap.add_argument("--out",default="logs/gate_b_support_both_years.json")
    args=ap.parse_args()

    df=pd.read_csv(args.samples)
    fit=df[df["split"].isin(["train","val"])].copy()
    test=df[df["split"]=="test"].copy()

    Xfit=fit[FEATURES].to_numpy()
    scaler=StandardScaler().fit(Xfit)
    Zfit=scaler.transform(Xfit)

    ncomp=min(16,Zfit.shape[1],max(2,Zfit.shape[0]-1))
    pca=PCA(n_components=ncomp,random_state=42).fit(Zfit)
    Pfit=pca.transform(Zfit)

    # Leave-one-out support threshold from the actual training manifold.
    nn2=NearestNeighbors(n_neighbors=2).fit(Pfit)
    d2,_=nn2.kneighbors(Pfit)
    loo=d2[:,1]
    threshold=float(np.percentile(loo,args.percentile))

    nn=NearestNeighbors(n_neighbors=1).fit(Pfit)

    years={}
    for year in [2017,2025]:
        mask_path=f"outputs/support_mask_{year}.tif"
        years[str(year)]=apply_support(
            f"data/olmoearth_hcmc_{year}_64d.tif",
            scaler,pca,nn,threshold,mask_path
        )
        years[str(year)]["support_mask_tif"]=mask_path
        rel_path=f"outputs/reliable_landcover_{year}.tif"
        years[str(year)]["reliability_map"]=make_reliable_map(
            f"outputs/landcover_{year}.tif",
            f"outputs/confidence_{year}.tif",
            mask_path,
            rel_path,
            args.confidence_threshold
        )
        years[str(year)]["reliable_landcover_tif"]=rel_path

    # Test support
    Ptest=pca.transform(scaler.transform(test[FEATURES].to_numpy()))
    dtest=nn.kneighbors(Ptest,return_distance=True)[0][:,0]

    result={
        "pca_components":int(ncomp),
        "pca_explained_variance_ratio_sum":float(pca.explained_variance_ratio_.sum()),
        "support_percentile":args.percentile,
        "support_distance_threshold":threshold,
        "fit_leave_one_out_distance":{
            "median":float(np.median(loo)),
            "p95":float(np.quantile(loo,0.95)),
            "max":float(loo.max())
        },
        "test_supported_fraction":float((dtest<=threshold).mean()),
        "confidence_threshold":args.confidence_threshold,
        "years":years,
        "interpretation":"Final reliable maps require both classifier confidence and embedding-manifold support. Original class maps remain untouched."
    }

    Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    Path(args.out).write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    main()
