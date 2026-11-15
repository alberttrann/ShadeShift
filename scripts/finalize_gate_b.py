import json,argparse
from pathlib import Path

def load(p):
    try:
        return json.loads(Path(p).read_text(encoding='utf-8'))
    except:
        return None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',default='.')
    args=ap.parse_args()
    r=Path(args.root)

    freeze=load(r/'logs/gate_b_label_freeze_v2.json')
    geo=load(r/'logs/gate_b_georef_qa.json')
    split=load(r/'logs/gate_b_label_split.json')
    samp=load(r/'logs/gate_b_sample_report.json')
    eva=load(r/'logs/gate_b_evaluation.json')
    pred=load(r/'logs/gate_b_prediction_report.json')
    hist=load(r/'logs/gate_b_historical_controls.json')
    vis=load(r/'logs/gate_b_visual_review.json')

    checks={
        'label_set_v2_frozen':bool(freeze and freeze.get('status')=='LABEL_SET_FROZEN'),
        'georef_pass':bool(geo and geo.get('gate_b_preflight_georef_pass')),
        'label_spatial_split_pass':bool(split and split.get('label_split_pass')),
        'embedding_sampling_pass':bool(samp and samp.get('sample_pass')),
        'heldout_evaluation_exists':bool(eva and eva.get('heldout_test',{}).get('macro_f1') is not None),
        'classification_maps_exist':all(
            (r/f'outputs/landcover_{y}.tif').exists()
            and (r/f'public/layers/landcover_{y}.png').exists()
            for y in [2017,2025]
        ),
        'unknown_mask_recorded':bool(pred and all('unknown_fraction' in x for x in pred.get('years',[]))),
        'historical_control_sanity_pass':bool(hist and hist.get('historical_control_pass')),
        'manual_2025_map_review_pass':bool(
            vis
            and vis.get('inspected')
            and vis.get('map_2025_readable')
            and vis.get('water_alignment_obvious')
            and vis.get('built_areas_plausible')
            and vis.get('vegetation_areas_plausible')
            and vis.get('unknown_mask_not_hiding_systematic_errors')
        ),
    }

    result={
        'gate':'B',
        'revision':'v2',
        'ontology_version':'ShadeShift-v2-3class',
        'status':'PASSED' if all(checks.values()) else 'NOT_PASSED_YET',
        'gate_b_pass':all(checks.values()),
        'checks':checks,
        'selected_model':eva.get('selected_model') if eva else None,
        'heldout_test_macro_f1':eva.get('heldout_test',{}).get('macro_f1') if eva else None,
        'scientific_note':'Metrics are against frozen weak multi-source labels, not independent human ground truth. Final whole-map visual review is mandatory.'
    }

    (r/'logs/gate_b_status.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['gate_b_pass'] else 7)

if __name__=='__main__':
    main()
