import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, log_loss, brier_score_loss
from sklearn.preprocessing import label_binarize

CLASSES=[1,2,4]
FEATURES=[f"f{i:02d}" for i in range(64)]

def make_model():
    return Pipeline([
        ("scale",StandardScaler()),
        ("clf",LogisticRegression(class_weight="balanced",max_iter=5000,random_state=42))
    ])

def ece(conf,correct,bins=10):
    edges=np.linspace(0,1,bins+1)
    total=len(conf); score=0.0; detail=[]
    for i in range(bins):
        lo,hi=edges[i],edges[i+1]
        mask=(conf>=lo)&((conf<hi) if i<bins-1 else (conf<=hi))
        if mask.sum()==0: continue
        acc=float(correct[mask].mean())
        c=float(conf[mask].mean())
        score += mask.sum()/total * abs(acc-c)
        detail.append({"lo":float(lo),"hi":float(hi),"n":int(mask.sum()),"accuracy":acc,"mean_confidence":c})
    return float(score),detail

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--samples",default="labels/embedding_samples_2025.csv")
    ap.add_argument("--out",default="logs/gate_b_oof_calibration.json")
    args=ap.parse_args()

    df=pd.read_csv(args.samples)
    group_col="spatial_group" if "spatial_group" in df.columns else "spatial_group_100m"
    X=df[FEATURES]; y=df["label"].astype(int); groups=df[group_col].astype(int)
    probs=np.full((len(df),len(CLASSES)),np.nan,dtype=float)

    gkf=GroupKFold(n_splits=5)
    for tr,te in gkf.split(X,y,groups):
        m=make_model()
        m.fit(X.iloc[tr],y.iloc[tr])
        p=m.predict_proba(X.iloc[te])
        # reorder columns to CLASSES
        order=[list(m.classes_).index(k) for k in CLASSES]
        probs[te]=p[:,order]

    valid=np.isfinite(probs).all(axis=1)
    yy=y.to_numpy()[valid]
    pp=probs[valid]
    pred=np.array(CLASSES)[np.argmax(pp,axis=1)]
    conf=pp.max(axis=1)
    correct=(pred==yy).astype(float)
    e,detail=ece(conf,correct,10)

    ybin=label_binarize(yy,classes=CLASSES)
    multiclass_brier=float(np.mean(np.sum((pp-ybin)**2,axis=1)))
    result={
        "n_oof":int(valid.sum()),
        "macro_f1":float(f1_score(yy,pred,labels=CLASSES,average="macro",zero_division=0)),
        "accuracy":float(correct.mean()),
        "mean_confidence":float(conf.mean()),
        "median_confidence":float(np.median(conf)),
        "ece_10bin":e,
        "multiclass_brier":multiclass_brier,
        "log_loss":float(log_loss(yy,pp,labels=CLASSES)),
        "bins":detail,
        "warning":"Small weak-label dataset; calibration statistics are diagnostic, not deployment-grade estimates."
    }
    Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    Path(args.out).write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    main()
