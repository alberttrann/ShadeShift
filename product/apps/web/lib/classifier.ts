export type ContextLayer = "none" | "landcover" | "vegToBuilt";

export type CellClassifierContext = {
  coordinates: [
    [number, number],
    [number, number],
    [number, number],
    [number, number]
  ];
  width: number;
  height: number;
  landcover_url: string;
  veg_to_built_url: string;
  counts: {
    vegetation: number;
    built: number;
    water: number;
    unknown_or_masked: number;
    veg_to_built: number;
  };
};

export type GlobalClassifierContext = {
  coordinates: [
    [number, number],
    [number, number],
    [number, number],
    [number, number]
  ];
  width: number;
  height: number;
  landcover_url: string;
  veg_to_built_url: string;
};

export type ClassifierMetadata = {
  version: string;
  eligible_cell_count: number;
  global: GlobalClassifierContext;
  cells: Record<string, CellClassifierContext>;
};

let cached: Promise<ClassifierMetadata | null> | null = null;

export function loadClassifierMetadata(): Promise<ClassifierMetadata | null> {
  if (!cached) {
    cached = fetch("/data/classifier/metadata.json", {
      cache: "no-store",
    })
      .then(async (response) => {
        if (!response.ok) return null;
        return (await response.json()) as ClassifierMetadata;
      })
      .catch(() => null);
  }

  return cached;
}
