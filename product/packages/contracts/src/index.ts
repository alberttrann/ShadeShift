import { z } from "zod";

export const EvidenceGradeSchema = z.enum(["A", "B", "C"]);
export const RawEvidenceGradeSchema = z.enum(["A", "B", "C", "unranked"]);
export type EvidenceGrade = z.infer<typeof EvidenceGradeSchema>;

export const TemporalStrengthSchema = z.enum(["strong", "moderate", "limited"]);
export type TemporalStrength = z.infer<typeof TemporalStrengthSchema>;

export const QaStrengthSchema = z.enum([
  "strong",
  "moderate",
  "insufficient",
  "discordant",
]);
export type QaStrength = z.infer<typeof QaStrengthSchema>;

export const SpatialStrengthSchema = z.enum([
  "full",
  "strong_partial",
  "minimum_supported",
  "unsupported",
]);
export type SpatialStrength = z.infer<typeof SpatialStrengthSchema>;

const NullableNumber = z.number().finite().nullable();

export const PolygonGeometrySchema = z.object({
  type: z.literal("Polygon"),
  coordinates: z.array(z.array(z.array(z.number()).min(2)).min(4)).min(1),
});

export const MultiPolygonGeometrySchema = z.object({
  type: z.literal("MultiPolygon"),
  coordinates: z
    .array(z.array(z.array(z.array(z.number()).min(2)).min(4)).min(1))
    .min(1),
});

export const GeometrySchema = z.union([
  PolygonGeometrySchema,
  MultiPolygonGeometrySchema,
]);
export type Geometry = z.infer<typeof GeometrySchema>;

export const RawCellPropertiesSchema = z
  .object({
    cell_id: z.string().min(1),
    footprint_overlap_fraction: z.number().min(0).max(1),
    spatial_support_ok: z.boolean(),
    known_fraction: z.number().min(0).max(1),
    terrestrial_share_of_known: z.number().min(0).max(1),
    vegetation_fraction_terrestrial: NullableNumber,
    built_fraction_terrestrial: NullableNumber,
    water_fraction_known: NullableNumber,
    historical_v2b_fraction_joint_reliable: NullableNumber,

    heat_score: NullableNumber,
    heat_scene_count: z.number().int().min(0),
    heat_scene_fraction: z.number().min(0).max(1),
    heat_rank_iqr: NullableNumber,
    hot_recurrence: NullableNumber,
    guarded_heat_score: NullableNumber,
    guarded_scene_count: z.number().int().min(0),
    qa_tier_heat_gap: NullableNumber,

    greening_need: NullableNumber,
    priority_core: NullableNumber,
    eligible: z.boolean(),
    priority_rank: NullableNumber,
    evidence_coverage_score: z.number().min(0).max(1),
    evidence_reason: z.string(),

    evidence_grade: RawEvidenceGradeSchema.optional(),
    temporal_evidence_strength: TemporalStrengthSchema.optional(),
    qa_corroboration_strength: QaStrengthSchema.optional(),
    spatial_evidence_strength: SpatialStrengthSchema.optional(),
    evidence_caveats: z.string().optional(),

    heat_loo_median_range: NullableNumber.optional(),
    paired_qa_scene_count: z.number().int().min(0).optional(),
    paired_qa_consensus_gap: NullableNumber.optional(),
    partial_validation_count: z.number().int().min(0).optional(),
    partial_validation_median_gap: NullableNumber.optional(),
    high_confidence_priority_rank: NullableNumber.optional(),
  })
  .passthrough();

export type RawCellProperties = z.infer<typeof RawCellPropertiesSchema>;

export const RawCellFeatureSchema = z.object({
  type: z.literal("Feature"),
  properties: RawCellPropertiesSchema,
  geometry: GeometrySchema,
});

export type RawCellFeature = z.infer<typeof RawCellFeatureSchema>;

export const RawPlanningCellsSchema = z.object({
  type: z.literal("FeatureCollection"),
  name: z.string().optional(),
  crs: z.unknown().optional(),
  features: z.array(RawCellFeatureSchema),
});

export type RawPlanningCells = z.infer<typeof RawPlanningCellsSchema>;

export const EnhancedPriorityRecordSchema = z
  .object({
    cell_id: z.string(),
    priority_rank: z.number().int().positive(),
    priority_core: z.number(),
    heat_score: z.number(),
    greening_need: z.number(),
    evidence_grade: EvidenceGradeSchema,
    temporal_evidence_strength: TemporalStrengthSchema,
    qa_corroboration_strength: QaStrengthSchema,
    spatial_evidence_strength: SpatialStrengthSchema,
    heat_scene_count: z.number().int().min(0),
    heat_loo_median_range: NullableNumber,
    paired_qa_scene_count: z.number().int().min(0),
    paired_qa_consensus_gap: NullableNumber,
    partial_validation_count: z.number().int().min(0),
    partial_validation_median_gap: NullableNumber,
    footprint_overlap_fraction: z.number().min(0).max(1),
    evidence_coverage_score: z.number().min(0).max(1),
    evidence_caveats: z.string(),
    evidence_reason: z.string(),
    high_confidence_priority_rank: z.number().int().positive().optional(),
  })
  .passthrough();

export type EnhancedPriorityRecord = z.infer<
  typeof EnhancedPriorityRecordSchema
>;

export const EnhancedPriorityListSchema = z.array(EnhancedPriorityRecordSchema);

export type MapMode = "priority" | "heat" | "greening" | "evidence";

export interface EvidenceDto {
  grade: EvidenceGrade | null;
  temporalStrength: TemporalStrength | null;
  qaStrength: QaStrength | null;
  spatialStrength: SpatialStrength | null;
  coverage: number;
  footprintOverlap: number;
  caveats: string[];
}

export interface CellMapPropertiesDto {
  cellId: string;
  eligible: boolean;
  priorityRank: number | null;
  priorityScore: number | null;
  heatScore: number | null;
  greeningNeed: number | null;
  evidenceGrade: EvidenceGrade | null;
  evidenceCoverage: number;
  footprintOverlap: number;
  heatSceneCount: number;
  hotRecurrence: number | null;
}

export interface CellMapFeatureDto {
  type: "Feature";
  geometry: Geometry;
  properties: CellMapPropertiesDto;
}

export interface CellMapFeatureCollectionDto {
  type: "FeatureCollection";
  features: CellMapFeatureDto[];
}

export interface CellDetailDto {
  cellId: string;
  geometry: Geometry;
  priority: {
    rank: number | null;
    score: number | null;
    eligible: boolean;
    highConfidenceRank: number | null;
  };
  heat: {
    score: number | null;
    sceneCount: number;
    sceneFraction: number;
    hotRecurrence: number | null;
    rankIqr: number | null;
    guardedScore: number | null;
    guardedSceneCount: number;
    legacyQaGap: number | null;
    looMedianRange: number | null;
    pairedQaSceneCount: number | null;
    pairedQaConsensusGap: number | null;
    partialValidationCount: number | null;
    partialValidationMedianGap: number | null;
  };
  landCover: {
    greeningNeed: number | null;
    builtFraction: number | null;
    vegetationFraction: number | null;
    waterFractionKnown: number | null;
    terrestrialShareOfKnown: number;
  };
  historical: {
    vegetationToBuiltFractionJointReliable: number | null;
  };
  evidence: EvidenceDto;
  reason: string[];
}

export interface PriorityListItemDto {
  cellId: string;
  priorityRank: number;
  priorityScore: number;
  heatScore: number;
  greeningNeed: number;
  evidence: EvidenceDto;
  heatSceneCount: number;
  heatLooMedianRange: number | null;
  pairedQaConsensusGap: number | null;
  partialValidationCount: number;
  partialValidationMedianGap: number | null;
  reason: string[];
  highConfidencePriorityRank?: number;
}

export interface MetaDto {
  scienceRevision: string;
  productRevision: string;
  totalCells: number;
  eligibleCells: number;
  evidenceGrades: Record<string, number>;
  artifacts: Record<
    string,
    { filename: string; sha256: string; enhanced: boolean }
  >;
  semantics: {
    priority: string;
    heat: string;
    evidenceGrade: string;
    ecostressRole: string;
  };
}

export interface LayerDefinitionDto {
  id: MapMode;
  label: string;
  field: keyof CellMapPropertiesDto;
  description: string;
}

export interface MethodologyDto {
  question: string;
  priorityFormula: string;
  heatDefinition: string;
  greeningDefinition: string;
  evidenceDefinition: string;
  historicalRole: string;
  ecostressRole: string;
  limitations: string[];
}

export function splitEvidenceReason(reason: string): string[] {
  return reason
    .split(";")
    .map((x) => x.trim())
    .filter(Boolean);
}

export function splitCaveats(caveats?: string): string[] {
  if (!caveats) return [];
  return caveats
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
}
