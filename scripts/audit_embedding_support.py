import argparse,json
from pathlib import Path
import numpy as np,pandas as pd,rasterio
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.neighbors import NearestNeighbors

FEATURES=[f"f{i:02d}" for i in range(64)]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--samples",default="labels/embedding_samples_2025.csv")
    ap.add_argument("--raster2025",default="data/olmoearth_hcmc_2025_64d.tif")
    ap.add_argument("--out-json",default="logs/gate_b_embedding_support.json")
    ap.add_argument("--out-tif",default="outputs/support_mask_2025.tif")
    ap.add_argument("--percentile",type=float,default=95.0)
    args=ap.parse_args()

    df=pd.read_csv(args.samples)
    # Fit support model on train+val, matching final classifier training support.
    fit=df[df["split"].isin(["train","val"])].copy()
    test=df[df["split"]=="test"].copy()

    Xfit=fit[FEATURES].to_numpy()
    Xtest=test[FEATURES].to_numpy()

    scaler=StandardScaler().fit(Xfit)
    Zfit=scaler.transform(Xfit)

    ncomp=min(16,Zfit.shape[1],max(2,Zfit.shape[0]-1))
    pca=PCA(n_components=ncomp,random_state=42).fit(Zfit)
    Pfit=pca.transform(Zfit)
    Ptest=pca.transform(scaler.transform(Xtest))

    # Leave-one-out nearest-neighbor distances within fit labels.
    nn2=NearestNeighbors(n_neighbors=2).fit(Pfit)
    d2,_=nn2.kneighbors(Pfit)
    loo=d2[:,1]
    threshold=float(np.percentile(loo,args.percentile))

    nn=NearestNeighbors(n_neighbors=1).fit(Pfit)
    dtest,_=nn.kneighbors(Ptest)
    dtest=dtest[:,0]

    with rasterio.open(args.raster2025) as ds:
        arr=ds.read().astype("float32")
        valid=np.isfinite(arr).all(axis=0)
        Xmap=arr[:,valid].T
        dist=np.empty(len(Xmap),dtype="float32")
        batch=50000
        for st in range(0,len(Xmap),batch):
            en=min(st+batch,len(Xmap))
            P=pca.transform(scaler.transform(Xmap[st:en]))
            dist[st:en]=nn.kneighbors(P,return_distance=True)[0][:,0].astype("float32")

        support=dist<=threshold
        mask=np.full(valid.shape,255,dtype="uint8")
        mask[valid]=np.where(support,1,0).astype("uint8")

        profile=ds.profile.copy()
        profile.update(count=1,dtype="uint8",nodata=255,compress="deflate")
        Path(args.out_tif).parent.mkdir(parents=True,exist_ok=True)
        with rasterio.open(args.out_tif,"w",**profile) as out:
            out.write(mask,1)

    result={
        "pca_components":int(ncomp),
        "pca_explained_variance_ratio_sum":float(pca.explained_variance_ratio_.sum()),
        "support_distance_percentile":args.percentile,
        "support_distance_threshold":threshold,
        "fit_leave_one_out_distance":{
            "median":float(np.median(loo)),
            "p95":float(np.quantile(loo,0.95)),
            "max":float(loo.max())
        },
        "test_distance":{
            "median":float(np.median(dtest)),
            "p95":float(np.quantile(dtest,0.95)),
            "max":float(dtest.max()),
            "supported_fraction":float((dtest<=threshold).mean())
        },
        "map_2025_supported_fraction":float(support.mean()),
        "map_2025_unsupported_fraction":float((~support).mean()),
        "support_mask_tif":args.out_tif,
        "interpretation":"Distance support is complementary to classifier probability. Unsupported pixels are far from the train+val embedding manifold under this PCA+kNN diagnostic."
    }
    Path(args.out_json).parent.mkdir(parents=True,exist_ok=True)
    Path(args.out_json).write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    main()
