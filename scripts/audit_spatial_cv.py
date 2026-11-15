import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, confusion_matrix

CSV = Path("labels/embedding_samples_2025.csv")
OUT = Path("logs/gate_b_spatial_cv.json")
CLASSES = [1, 2, 4]

df = pd.read_csv(CSV)
features = [f"f{i:02d}" for i in range(64)]
group_col = "spatial_group" if "spatial_group" in df.columns else "spatial_group_100m"
if group_col not in df.columns:
    raise SystemExit("No spatial-group column found in embedding_samples_2025.csv")

X = df[features]
y = df["label"].astype(int)
groups = df[group_col]

models = {
    "logistic": lambda: Pipeline([
        ("scale", StandardScaler()),
        ("clf", LogisticRegression(
            class_weight="balanced",
            max_iter=5000,
            random_state=42
        ))
    ]),
    "random_forest": lambda: RandomForestClassifier(
        n_estimators=400,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1
    )
}

n_splits = min(5, groups.nunique())
gkf = GroupKFold(n_splits=n_splits)
result = {
    "n_samples": len(df),
    "n_groups": int(groups.nunique()),
    "n_splits": n_splits,
    "classes": CLASSES,
    "label_protocol": "weak_multisource_consensus_v2",
    "warning": "CV measures agreement with frozen weak labels, not independent human ground truth.",
    "models": {}
}

for name, factory in models.items():
    folds = []
    cms = []
    for fold, (tr, te) in enumerate(gkf.split(X, y, groups)):
        m = factory()
        m.fit(X.iloc[tr], y.iloc[tr])
        p = m.predict(X.iloc[te])
        mf1 = f1_score(y.iloc[te], p, labels=CLASSES, average="macro", zero_division=0)
        cm = confusion_matrix(y.iloc[te], p, labels=CLASSES)
        folds.append(float(mf1))
        cms.append(cm)

    cm_sum = np.sum(cms, axis=0)
    result["models"][name] = {
        "fold_macro_f1": folds,
        "mean_macro_f1": float(np.mean(folds)),
        "std_macro_f1": float(np.std(folds, ddof=1)) if len(folds) > 1 else 0.0,
        "min_macro_f1": float(np.min(folds)),
        "max_macro_f1": float(np.max(folds)),
        "summed_confusion_matrix": cm_sum.tolist()
    }

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
