import type {
  CellDetailDto,
  CellMapFeatureCollectionDto,
  MetaDto,
  MethodologyDto,
  PriorityListItemDto,
} from "@shadeshift/contracts";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:4000/api/v1";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${body}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  meta: () => getJson<MetaDto>("/meta"),
  cells: () => getJson<CellMapFeatureCollectionDto>("/cells"),
  cell: (id: string) => getJson<CellDetailDto>(`/cells/${id}`),
  top: (strongEvidenceOnly = false) =>
    getJson<PriorityListItemDto[]>(
      `/priorities/top?limit=10&strongEvidenceOnly=${strongEvidenceOnly}`,
    ),
  methodology: () => getJson<MethodologyDto>("/methodology"),
};
