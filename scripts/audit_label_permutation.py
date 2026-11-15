import argparse, json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score

CLASSES=[1,2,4]
FEATURES=[f"f{i:02d}" for i in range(64)]

def model():
    return Pipeline([
        ("scale",StandardScaler()),
        ("clf",LogisticRegression(class_weight="balanced",max_iter=5000,random_state=42))
    ])

def grouped_cv_score(X,y,groups):
    gkf=GroupKFold(n_splits=5)
    vals=[]
    for tr,te in gkf.split(X,y,groups):
        if set(y.iloc[tr].unique())!=set(CLASSES) or set(y.iloc[te].unique())!=set(CLASSES):
            continue
        m=model()
        m.fit(X.iloc[tr],y.iloc[tr])
        p=m.predict(X.iloc[te])
        vals.append(f1_score(y.iloc[te],p,labels=CLASSES,average="macro",zero_division=0))
    return float(np.mean(vals)) if vals else None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--samples",default="labels/embedding_samples_2025.csv")
    ap.add_argument("--permutations",type=int,default=300)
    ap.add_argument("--out",default="logs/gate_b_label_permutation_test.json")
    args=ap.parse_args()

    df=pd.read_csv(args.samples)
    group_col="spatial_group" if "spatial_group" in df.columns else "spatial_group_100m"
    X=df[FEATURES]
    y=df["label"].astype(int)
    groups=df[group_col].astype(int)

    observed=grouped_cv_score(X,y,groups)
    if observed is None:
        raise SystemExit("Could not compute observed grouped CV score")

    rng=np.random.default_rng(2026)
    null=[]
    y0=y.to_numpy()
    for _ in range(args.permutations):
        yp=pd.Series(rng.permutation(y0),index=y.index)
        s=grouped_cv_score(X,yp,groups)
        if s is not None:
            null.append(s)

    null=np.array(null,dtype=float)
    p=float((1+np.sum(null>=observed))/(1+len(null)))
    result={
        "observed_grouped_cv_macro_f1":observed,
        "permutations_completed":int(len(null)),
        "null_mean_macro_f1":float(null.mean()),
        "null_std_macro_f1":float(null.std(ddof=1)),
        "null_p95_macro_f1":float(np.quantile(null,0.95)),
        "empirical_p_value":p,
        "interpretation":"Low p-value indicates OlmoEarth embeddings contain class signal beyond label-frequency chance under this frozen weak-label protocol."
    }
    Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    Path(args.out).write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    main()
