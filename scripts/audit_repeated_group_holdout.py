import argparse, json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, confusion_matrix

CLASSES=[1,2,4]
FEATURES=[f"f{i:02d}" for i in range(64)]

def make_models():
    return {
        "logistic": Pipeline([
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(class_weight="balanced", max_iter=5000, random_state=42))
        ]),
        "random_forest": RandomForestClassifier(
            n_estimators=400, min_samples_leaf=2,
            class_weight="balanced_subsample", random_state=42, n_jobs=-1
        )
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--samples", default="labels/embedding_samples_2025.csv")
    ap.add_argument("--repeats", type=int, default=200)
    ap.add_argument("--test-size", type=float, default=0.20)
    ap.add_argument("--out", default="logs/gate_b_repeated_group_holdout.json")
    args=ap.parse_args()

    df=pd.read_csv(args.samples)
    group_col="spatial_group" if "spatial_group" in df.columns else "spatial_group_100m"
    if group_col not in df.columns:
        raise SystemExit("Missing spatial group column")

    X=df[FEATURES]
    y=df["label"].astype(int)
    groups=df[group_col].astype(int)

    splitter=GroupShuffleSplit(n_splits=args.repeats*5, test_size=args.test_size, random_state=2026)
    store={m:[] for m in make_models()}
    accepted_splits=0

    for tr,te in splitter.split(X,y,groups):
        if accepted_splits>=args.repeats:
            break
        if set(y.iloc[tr].unique())!=set(CLASSES) or set(y.iloc[te].unique())!=set(CLASSES):
            continue
        # require at least 4 per class in test to avoid pathological tiny class support
        if min((y.iloc[te]==k).sum() for k in CLASSES) < 4:
            continue

        models=make_models()
        for name,m in models.items():
            m.fit(X.iloc[tr], y.iloc[tr])
            p=m.predict(X.iloc[te])
            store[name].append({
                "macro_f1": float(f1_score(y.iloc[te],p,labels=CLASSES,average="macro",zero_division=0)),
                "test_n": int(len(te)),
                "test_support": {str(k):int((y.iloc[te]==k).sum()) for k in CLASSES},
                "confusion_matrix": confusion_matrix(y.iloc[te],p,labels=CLASSES).tolist()
            })
        accepted_splits+=1

    if accepted_splits < max(30, args.repeats//2):
        raise SystemExit(f"Only {accepted_splits} valid group splits found")

    result={"accepted_splits":accepted_splits,"test_size":args.test_size,"classes":CLASSES,"models":{}}
    for name,rows in store.items():
        vals=np.array([r["macro_f1"] for r in rows],dtype=float)
        result["models"][name]={
            "mean_macro_f1":float(vals.mean()),
            "std_macro_f1":float(vals.std(ddof=1)),
            "median_macro_f1":float(np.median(vals)),
            "p05_macro_f1":float(np.quantile(vals,0.05)),
            "p25_macro_f1":float(np.quantile(vals,0.25)),
            "p75_macro_f1":float(np.quantile(vals,0.75)),
            "p95_macro_f1":float(np.quantile(vals,0.95)),
            "min_macro_f1":float(vals.min()),
            "max_macro_f1":float(vals.max())
        }

    Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    Path(args.out).write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    main()
