import argparse,json
from pathlib import Path
import joblib, numpy as np, pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, confusion_matrix, classification_report

CLASSES=[1,2,4]
NAMES=['vegetation','built','water']

def metrics(y,p):
    return {
        'macro_f1':float(f1_score(y,p,labels=CLASSES,average='macro',zero_division=0)),
        'confusion_matrix':confusion_matrix(y,p,labels=CLASSES).tolist(),
        'classification_report':classification_report(
            y,p,labels=CLASSES,target_names=NAMES,output_dict=True,zero_division=0
        )
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--samples',default='labels/embedding_samples_2025.csv')
    ap.add_argument('--model-out',default='models/landcover_model.joblib')
    ap.add_argument('--eval-out',default='logs/gate_b_evaluation.json')
    args=ap.parse_args()

    df=pd.read_csv(args.samples)
    feats=[f'f{i:02d}' for i in range(64)]

    unexpected=sorted(set(df.label.astype(int))-set(CLASSES))
    if unexpected:
        raise SystemExit(f'Unexpected labels for V2 ontology: {unexpected}')

    tr=df[df.split=='train']
    va=df[df.split=='val']
    te=df[df.split=='test']

    for name,d in [('train',tr),('val',va),('test',te)]:
        if len(d)==0:
            raise SystemExit(f'No {name} samples')
        missing=set(CLASSES)-set(d.label.astype(int).unique())
        if missing:
            raise SystemExit(f'{name} missing classes: {sorted(missing)}')

    candidates={
        'logistic':Pipeline([
            ('scale',StandardScaler()),
            ('clf',LogisticRegression(
                class_weight='balanced',
                max_iter=5000,
                random_state=42
            ))
        ]),
        'random_forest':RandomForestClassifier(
            n_estimators=400,
            min_samples_leaf=2,
            class_weight='balanced_subsample',
            random_state=42,
            n_jobs=-1
        )
    }

    val_results={}
    for name,m in candidates.items():
        m.fit(tr[feats],tr.label)
        pred=m.predict(va[feats])
        val_results[name]=metrics(va.label,pred)

    selected=max(
        val_results,
        key=lambda n:(val_results[n]['macro_f1'],1 if n=='logistic' else 0)
    )

    final_model=candidates[selected]
    trainval=pd.concat([tr,va],ignore_index=True)
    final_model.fit(trainval[feats],trainval.label)

    ptest=final_model.predict(te[feats])
    test_result=metrics(te.label,ptest)

    if hasattr(final_model,'predict_proba'):
        conf=final_model.predict_proba(te[feats]).max(axis=1)
        test_result['confidence_heuristic_mean']=float(np.mean(conf))
        test_result['confidence_heuristic_median']=float(np.median(conf))

    bundle={
        'model':final_model,
        'feature_names':feats,
        'classes':CLASSES,
        'class_names':NAMES,
        'selected_model':selected,
        'trained_on':'train+val',
        'confidence_is_calibrated':False,
        'ontology_version':'ShadeShift-v2-3class'
    }

    Path(args.model_out).parent.mkdir(parents=True,exist_ok=True)
    joblib.dump(bundle,args.model_out)

    result={
        'ontology_version':'ShadeShift-v2-3class',
        'selected_model':selected,
        'selection_basis':'validation macro-F1; logistic wins exact tie',
        'validation_results':val_results,
        'heldout_test':test_result,
        'support':{
            'train':{str(k):int(v) for k,v in tr.label.value_counts().sort_index().items()},
            'val':{str(k):int(v) for k,v in va.label.value_counts().sort_index().items()},
            'test':{str(k):int(v) for k,v in te.label.value_counts().sort_index().items()}
        },
        'label_protocol':'weak_multisource_consensus_v2',
        'metric_warning':'Held-out test measures agreement with frozen weak labels; it is not an independent human-ground-truth accuracy estimate.',
        'confidence_warning':'max predict_proba is an uncalibrated confidence heuristic'
    }

    Path(args.eval_out).parent.mkdir(parents=True,exist_ok=True)
    Path(args.eval_out).write_text(
        json.dumps(result,indent=2,default=lambda x:int(x) if hasattr(x,'item') else str(x)),
        encoding='utf-8'
    )
    print(json.dumps(result,indent=2,default=str))

if __name__=='__main__':
    main()
