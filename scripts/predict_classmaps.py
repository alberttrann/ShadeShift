import argparse,json
from pathlib import Path
import joblib, numpy as np, pandas as pd, rasterio
from PIL import Image

# Class 3 is intentionally retired in V2.
PALETTE={
    0:(128,128,128,160),   # unknown
    1:(46,139,87,220),     # vegetation
    2:(178,34,34,220),     # built
    4:(30,144,255,220),    # water
    255:(0,0,0,0)          # nodata
}

ACTIVE_CLASSES=[1,2,4]

def predict_one(raster_path, model_bundle, year, outdir, publicdir, threshold, batch=50000):
    model=model_bundle['model']

    with rasterio.open(raster_path) as ds:
        arr=ds.read().astype('float32')
        profile=ds.profile.copy()
        valid=np.isfinite(arr).all(axis=0)
        h,w=valid.shape

        X=arr[:,valid].T
        pred=np.full(valid.sum(),0,dtype='uint8')
        conf=np.full(valid.sum(),np.nan,dtype='float32')

        for st in range(0,len(X),batch):
            en=min(st+batch,len(X))
            xb=pd.DataFrame(X[st:en],columns=model_bundle['feature_names'])
            proba=model.predict_proba(xb)
            p=model.classes_[np.argmax(proba,axis=1)].astype('uint8')
            c=np.max(proba,axis=1).astype('float32')
            p[c<threshold]=0
            pred[st:en]=p
            conf[st:en]=c

        cls=np.full((h,w),255,dtype='uint8')
        cf=np.full((h,w),np.nan,dtype='float32')
        cls[valid]=pred
        cf[valid]=conf

        outdir.mkdir(parents=True,exist_ok=True)
        publicdir.mkdir(parents=True,exist_ok=True)

        cp=outdir/f'landcover_{year}.tif'
        fp=outdir/f'confidence_{year}.tif'

        profc=profile.copy()
        profc.update(count=1,dtype='uint8',nodata=255,compress='deflate')
        with rasterio.open(cp,'w',**profc) as dst:
            dst.write(cls,1)

        proff=profile.copy()
        proff.update(count=1,dtype='float32',nodata=np.nan,compress='deflate',predictor=3)
        with rasterio.open(fp,'w',**proff) as dst:
            dst.write(cf,1)

        rgba=np.zeros((h,w,4),dtype='uint8')
        for k,c in PALETTE.items():
            rgba[cls==k]=c
        Image.fromarray(rgba,'RGBA').save(publicdir/f'landcover_{year}.png')

        vals=cls[cls!=255]
        counts={str(k):int((vals==k).sum()) for k in [0,1,2,4]}

        return {
            'year':year,
            'width':w,
            'height':h,
            'valid_pixel_count':int(valid.sum()),
            'unknown_fraction':float((pred==0).mean()) if len(pred) else None,
            'class_counts':counts,
            'class_tif':str(cp),
            'confidence_tif':str(fp),
            'png':str(publicdir/f'landcover_{year}.png'),
            'transform':list(ds.transform)[:6],
            'crs':ds.crs.to_string()
        }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',default='.')
    ap.add_argument('--threshold',type=float,default=0.60)
    ap.add_argument('--report',default='logs/gate_b_prediction_report.json')
    args=ap.parse_args()
    root=Path(args.root)

    bundle=joblib.load(root/'models/landcover_model.joblib')
    if set(bundle.get('classes',[])) != set(ACTIVE_CLASSES):
        raise SystemExit(f"Model classes {bundle.get('classes')} do not match V2 ontology {ACTIVE_CLASSES}")

    res=[]
    for y in [2025,2017]:
        res.append(
            predict_one(
                root/f'data/olmoearth_hcmc_{y}_64d.tif',
                bundle,
                y,
                root/'outputs',
                root/'public/layers',
                args.threshold
            )
        )

    r={
        'ontology_version':'ShadeShift-v2-3class',
        'confidence_threshold':args.threshold,
        'confidence_calibrated':False,
        'years':res,
        'legend':{
            '0':'unknown',
            '1':'vegetation',
            '2':'built',
            '4':'water',
            '255':'nodata'
        },
        'retired_class':{'3':'bare_other'}
    }

    p=root/args.report
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(r,indent=2),encoding='utf-8')
    print(json.dumps(r,indent=2))

if __name__=='__main__':
    main()
