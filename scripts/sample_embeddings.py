import argparse,json
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd, rasterio


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--labels',default='labels/labels_split.geojson'); ap.add_argument('--raster',default='data/olmoearth_hcmc_2025_64d.tif'); ap.add_argument('--out',default='labels/embedding_samples_2025.csv'); ap.add_argument('--report',default='logs/gate_b_sample_report.json'); args=ap.parse_args()
    g=gpd.read_file(args.labels)
    with rasterio.open(args.raster) as ds:
        if ds.count!=64: raise SystemExit(f'Expected 64 bands, got {ds.count}')
        gg=g.to_crs(ds.crs)
        coords=[(p.x,p.y) for p in gg.geometry]
        vals=np.array(list(ds.sample(coords)),dtype='float32')
        valid=np.isfinite(vals).all(axis=1)
        rows=[]
        for i,(idx,r) in enumerate(g.iterrows()):
            if not valid[i]: continue
            d={'source_index':str(idx),'lon':float(r.geometry.x),'lat':float(r.geometry.y),'label':int(r.manual_label),'split':str(r.split),'spatial_group':int(r.spatial_group)}
            for j in range(64): d[f'f{j:02d}']=float(vals[i,j])
            rows.append(d)
    df=pd.DataFrame(rows); Path(args.out).parent.mkdir(parents=True,exist_ok=True); df.to_csv(args.out,index=False)
    counts=df.groupby(['split','label']).size().unstack(fill_value=0).to_dict(orient='index') if len(df) else {}
    rep={'sample_pass':len(df)==len(g),'requested_points':len(g),'valid_points':len(df),'dropped_invalid':int(len(g)-len(df)),'counts':counts}
    Path(args.report).parent.mkdir(parents=True,exist_ok=True); Path(args.report).write_text(json.dumps(rep,indent=2),encoding='utf-8'); print(json.dumps(rep,indent=2)); raise SystemExit(0 if rep['sample_pass'] else 5)
if __name__=='__main__': main()
