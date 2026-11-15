import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score,confusion_matrix

ALL_CLASSES=[1,2,4]
FEATURES=[f"f{i:02d}" for i in range(64)]

def py(v):
    if isinstance(v,(np.integer,)): return int(v)
    if isinstance(v,(np.floating,)): return float(v)
    if isinstance(v,np.ndarray): return v.tolist()
    raise TypeError(type(v).__name__)

def make_model():
    return Pipeline([
        ("scale",StandardScaler()),
        ("clf",LogisticRegression(class_weight="balanced",max_iter=5000,random_state=42))
    ])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--samples",default="labels/embedding_samples_2025.csv")
    ap.add_argument("--out",default="logs/gate_b_quadrant_holdout_v2.json")
    args=ap.parse_args()

    df=pd.read_csv(args.samples)
    if not {"lon","lat"}.issubset(df.columns):
        raise SystemExit("embedding_samples_2025.csv needs lon/lat columns")

    xmid=float(df.lon.median())
    ymid=float(df.lat.median())
    df["quadrant"]=np.where(
        df.lat>=ymid,
        np.where(df.lon>=xmid,"NE","NW"),
        np.where(df.lon>=xmid,"SE","SW")
    )

    rows=[]
    for q in ["NW","NE","SW","SE"]:
        te=df[df.quadrant==q]
        tr=df[df.quadrant!=q]
        present=sorted(int(x) for x in te.label.astype(int).unique())
        train_present=sorted(int(x) for x in tr.label.astype(int).unique())
        usable_classes=sorted(set(present).intersection(train_present))

        row={
            "quadrant":q,
            "test_n":int(len(te)),
            "test_support":{str(k):int((te.label==k).sum()) for k in ALL_CLASSES},
            "classes_present_in_test":present,
            "classes_present_in_train":train_present,
        }

        if len(usable_classes)<2:
            row["usable"]=False
            row["reason"]="Fewer than 2 evaluable classes"
            rows.append(row)
            continue

        m=make_model()
        m.fit(tr[FEATURES],tr.label)
        p=m.predict(te[FEATURES])

        row["usable"]=True
        row["observed_class_macro_f1"]=float(
            f1_score(te.label,p,labels=usable_classes,average="macro",zero_division=0)
        )
        row["observed_class_confusion_matrix"]=confusion_matrix(
            te.label,p,labels=usable_classes
        ).tolist()
        row["strict_3class_macro_f1"]=(
            float(f1_score(te.label,p,labels=ALL_CLASSES,average="macro",zero_division=0))
            if set(present)==set(ALL_CLASSES)
            else None
        )
        row["strict_3class_eligible"]=bool(set(present)==set(ALL_CLASSES))
        rows.append(row)

    strict=[r["strict_3class_macro_f1"] for r in rows if r.get("strict_3class_eligible")]
    observed=[r["observed_class_macro_f1"] for r in rows if r.get("usable")]

    result={
        "longitude_split":xmid,
        "latitude_split":ymid,
        "quadrants":rows,
        "strict_3class_quadrants":len(strict),
        "strict_3class_mean_macro_f1":float(np.mean(strict)) if strict else None,
        "observed_class_mean_macro_f1":float(np.mean(observed)) if observed else None,
        "note":"SE is evaluated on vegetation/built if no water labels occur there; strict 3-class score is only reported where all classes are present."
    }

    Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    Path(args.out).write_text(json.dumps(result,indent=2,default=py),encoding="utf-8")
    print(json.dumps(result,indent=2,default=py))

if __name__=="__main__":
    main()
