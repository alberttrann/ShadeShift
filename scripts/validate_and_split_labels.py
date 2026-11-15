import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
from sklearn.cluster import DBSCAN

CLASSES={1:'vegetation',2:'built',4:'water'}

def class_counts(df, split):
    s=df[df.split==split]
    return {str(k):int((s.manual_label==k).sum()) for k in CLASSES}

def meets(counts, mins):
    return all(counts.get(str(k),0)>=mins for k in CLASSES)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--labels', required=True)
    ap.add_argument('--out', default='labels/labels_split.geojson')
    ap.add_argument('--report', default='logs/gate_b_label_split.json')
    ap.add_argument('--min-train', type=int, default=20)
    ap.add_argument('--min-val', type=int, default=6)
    ap.add_argument('--min-test', type=int, default=8)
    ap.add_argument('--separation-m', type=float, default=100.0)
    ap.add_argument('--max-seed', type=int, default=10000)
    args=ap.parse_args()

    g=gpd.read_file(args.labels)
    if g.crs is None:
        g=g.set_crs('EPSG:4326')
    else:
        g=g.to_crs('EPSG:4326')

    req=['manual_label','verified']
    missing=[c for c in req if c not in g.columns]
    if missing:
        raise SystemExit(f'Missing fields: {missing}')

    g=g[pd.to_numeric(g.verified,errors='coerce').fillna(0).astype(int)==1].copy()
    g['manual_label']=pd.to_numeric(g.manual_label,errors='coerce').fillna(0).astype(int)
    g=g[g.manual_label.isin(CLASSES)].copy()

    unexpected=sorted(set(pd.to_numeric(g.manual_label,errors='coerce').dropna().astype(int))-set(CLASSES))
    if unexpected:
        raise SystemExit(f'Unexpected active classes: {unexpected}')
    if len(g)==0:
        raise SystemExit('No verified V2 labels found.')

    utm=g.to_crs('EPSG:32648')
    coords=np.c_[utm.geometry.x,utm.geometry.y]
    groups=DBSCAN(eps=args.separation_m,min_samples=1).fit_predict(coords)
    g['spatial_group']=groups.astype(int)

    unique_groups=np.unique(groups)
    best=None
    for seed in range(args.max_seed):
        rng=np.random.default_rng(seed)
        gids=unique_groups.copy()
        rng.shuffle(gids)

        n=len(gids)
        n_train=int(round(0.60*n))
        n_val=int(round(0.20*n))
        mapping={}
        for i,gid in enumerate(gids):
            mapping[int(gid)]='train' if i<n_train else ('val' if i<n_train+n_val else 'test')

        merged=g.copy()
        merged['split']=merged.spatial_group.map(mapping)

        ct={sp:class_counts(merged,sp) for sp in ['train','val','test']}
        ok=(meets(ct['train'],args.min_train)
            and meets(ct['val'],args.min_val)
            and meets(ct['test'],args.min_test))

        ratios=[]
        for sp,m in [('train',args.min_train),('val',args.min_val),('test',args.min_test)]:
            for k in CLASSES:
                ratios.append(ct[sp][str(k)]/m)
        score=min(ratios)

        if best is None or score>best[0]:
            best=(score,seed,merged,ct,ok)
        if ok:
            break

    if best is None:
        raise SystemExit('Could not construct leakage-safe spatial split.')

    score,seed,merged,ct,ok=best
    merged=gpd.GeoDataFrame(merged,geometry='geometry',crs=g.crs).sort_index()

    # Explicit leakage audit: no 100m group may appear in multiple splits.
    group_split_counts=merged.groupby('spatial_group')['split'].nunique()
    leakage_groups=int((group_split_counts>1).sum())
    ok=bool(ok and leakage_groups==0)

    Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    merged.to_file(args.out,driver='GeoJSON')

    report={
        'label_split_pass':ok,
        'ontology_version':'ShadeShift-v2-3class',
        'classes':CLASSES,
        'seed':seed,
        'separation_m':args.separation_m,
        'verified_total':len(g),
        'spatial_groups':int(merged.spatial_group.nunique()),
        'leakage_groups':leakage_groups,
        'counts':ct,
        'minimums':{'train':args.min_train,'val':args.min_val,'test':args.min_test},
        'label_protocol':'weak_multisource_consensus_v2',
        'warning':'Held-out metrics measure agreement with frozen weak labels, not independent human ground truth.'
    }
    Path(args.report).parent.mkdir(parents=True,exist_ok=True)
    Path(args.report).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if ok else 4)

if __name__=='__main__':
    main()
