import argparse,json
from pathlib import Path
import geopandas as gpd, pandas as pd, rasterio

ACTIVE_CLASSES=[1,2,4]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--labels',default='labels/labels_split.geojson')
    ap.add_argument('--map',default='outputs/landcover_2017.tif')
    ap.add_argument('--out',default='logs/gate_b_historical_controls.json')
    args=ap.parse_args()

    g=gpd.read_file(args.labels)
    if 'stable_2017' not in g.columns or 'label_2017' not in g.columns:
        raise SystemExit('Frozen labels need stable_2017 and label_2017 fields.')

    st=g[pd.to_numeric(g.stable_2017,errors='coerce').fillna(0).astype(int)==1].copy()
    st['label_2017']=pd.to_numeric(st.label_2017,errors='coerce').fillna(0).astype(int)
    st=st[st.label_2017.isin(ACTIVE_CLASSES)]

    with rasterio.open(args.map) as ds:
        pts=st.to_crs(ds.crs)
        vals=[int(x[0]) for x in ds.sample([(p.x,p.y) for p in pts.geometry])]

    st['pred_2017']=vals
    st['match']=st.pred_2017==st.label_2017

    reviewed=len(st)
    matches=int(st['match'].sum()) if reviewed else 0
    acc=matches/reviewed if reviewed else None

    byclass={
        str(k):{
            'n':int((st.label_2017==k).sum()),
            'matches':int(((st.label_2017==k)&st.match).sum())
        }
        for k in ACTIVE_CLASSES
    }

    result={
        'historical_control_pass':bool(reviewed>=8 and acc is not None and acc>=0.75),
        'reviewed_controls':reviewed,
        'matches':matches,
        'agreement':acc,
        'by_class':byclass,
        'control_protocol':'Dynamic World 2017 primary weak controls; not manually verified ground truth.',
        'rule':'At least 8 frozen weak historical controls and >=75% agreement. This is a transfer sanity check, not formal historical accuracy.'
    }

    Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    Path(args.out).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['historical_control_pass'] else 6)

if __name__=='__main__':
    main()
