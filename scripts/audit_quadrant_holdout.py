import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score,confusion_matrix

CLASSES=[1,2,4]
FEATURES=[f"f{i:02d}" for i in range(64)]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--samples",default="labels/embedding_samples_2025.csv")
    ap.add_argument("--out",default="logs/gate_b_quadrant_holdout.json")
    args=ap.parse_args()

    df=pd.read_csv(args.samples)
    if not {"lon","lat"}.issubset(df.columns):
        raise SystemExit("embedding_samples_2025.csv needs lon/lat columns")

    xmid=float(df.lon.median()); ymid=float(df.lat.median())
    df["quadrant"]=np.where(df.lat>=ymid,
        np.where(df.lon>=xmid,"NE","NW"),
        np.where(df.lon>=xmid,"SE","SW")
    )

    rows=[]
    for q in ["NW","NE","SW","SE"]:
        te=df[df.quadrant==q]
        tr=df[df.quadrant!=q]
        if len(te)==0 or set(te.label.astype(int).unique())!=set(CLASSES) or set(tr.label.astype(int).unique())!=set(CLASSES):
            rows.append({"quadrant":q,"usable":False,"test_n":int(len(te)),
                         "test_support":{str(k):int((te.label==k).sum()) for k in CLASSES}})
            continue
        m=Pipeline([
            ("scale",StandardScaler()),
            ("clf",LogisticRegression(class_weight="balanced",max_iter=5000,random_state=42))
        ])
        m.fit(tr[FEATURES],tr.label)
        p=m.predict(te[FEATURES])
        rows.append({
            "quadrant":q,"usable":True,"test_n":int(len(te)),
            "test_support":{str(k):int((te.label==k).sum()) for k in CLASSES},
            "macro_f1":float(f1_score(te.label,p,labels=CLASSES,average="macro",zero_division=0)),
            "confusion_matrix":confusion_matrix(te.label,p,labels=CLASSES).tolist()
        })

    result={"longitude_split":xmid,"latitude_split":ymid,"quadrants":rows}
    Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    Path(args.out).write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    main()
