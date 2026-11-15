import argparse,json
from pathlib import Path
import numpy as np,pandas as pd,rasterio

CLASSES=[0,1,2,4]
NAMES={0:"unknown",1:"vegetation",2:"built",4:"water"}
AREA=0.0001

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--map2017",default="outputs/reliable_landcover_2017.tif")
    ap.add_argument("--map2025",default="outputs/reliable_landcover_2025.tif")
    ap.add_argument("--out-json",default="logs/gate_b_reliable_transition_audit.json")
    ap.add_argument("--out-csv",default="logs/gate_b_reliable_transition_matrix.csv")
    ap.add_argument("--out-tif",default="outputs/reliable_change_code_2017_2025.tif")
    args=ap.parse_args()

    with rasterio.open(args.map2017) as a, rasterio.open(args.map2025) as b:
        if (a.width,a.height,a.crs,a.transform)!=(b.width,b.height,b.crs,b.transform):
            raise SystemExit("Reliable maps not aligned")
        x17=a.read(1); x25=b.read(1); profile=a.profile.copy()

    valid=(x17!=255)&(x25!=255)
    matrix=[]
    for i in CLASSES:
        matrix.append([int(np.sum(valid&(x17==i)&(x25==j))) for j in CLASSES])

    df=pd.DataFrame(matrix,index=[f"2017_{NAMES[i]}" for i in CLASSES],
                    columns=[f"2025_{NAMES[j]}" for j in CLASSES])
    Path(args.out_csv).parent.mkdir(parents=True,exist_ok=True)
    df.to_csv(args.out_csv)

    code=np.full(x17.shape,255,dtype="uint8")
    code[valid]=(10*x17[valid]+x25[valid]).astype("uint8")
    profile.update(count=1,dtype="uint8",nodata=255,compress="deflate")
    with rasterio.open(args.out_tif,"w",**profile) as dst:
        dst.write(code,1)

    def cnt(a,b):
        return int(np.sum(valid&(x17==a)&(x25==b)))

    reliable_nonunknown=valid&(x17!=0)&(x25!=0)
    changed=reliable_nonunknown&(x17!=x25)

    result={
        "valid_pixels":int(valid.sum()),
        "reliable_nonunknown_pixels":int(reliable_nonunknown.sum()),
        "reliable_nonunknown_fraction_of_valid":float(reliable_nonunknown.sum()/valid.sum()),
        "reliable_changed_pixels":int(changed.sum()),
        "reliable_changed_fraction_of_reliable_nonunknown":float(changed.sum()/reliable_nonunknown.sum()) if reliable_nonunknown.sum() else None,
        "matrix_classes":CLASSES,
        "transition_matrix":matrix,
        "key_transitions":{
            "vegetation_to_built":{"pixels":cnt(1,2),"area_km2":cnt(1,2)*AREA},
            "built_to_vegetation":{"pixels":cnt(2,1),"area_km2":cnt(2,1)*AREA},
            "water_to_built":{"pixels":cnt(4,2),"area_km2":cnt(4,2)*AREA},
            "built_to_water":{"pixels":cnt(2,4),"area_km2":cnt(2,4)*AREA},
        },
        "net_vegetation_to_built_exchange_km2":(cnt(1,2)-cnt(2,1))*AREA,
        "warning":"Reliable transitions require support+confidence, but still need imagery inspection before being described as verified real-world change."
    }
    Path(args.out_json).write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(df)
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    main()
