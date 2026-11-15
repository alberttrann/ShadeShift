import {
  Injectable,
  NotFoundException,
  OnModuleInit,
  ServiceUnavailableException,
} from "@nestjs/common";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  CellDetailDto,
  CellMapFeatureCollectionDto,
  CellMapFeatureDto,
  EnhancedPriorityListSchema,
  EnhancedPriorityRecord,
  EvidenceGrade,
  LayerDefinitionDto,
  MapMode,
  MetaDto,
  MethodologyDto,
  PriorityListItemDto,
  RawCellFeature,
  RawPlanningCells,
  RawPlanningCellsSchema,
  splitCaveats,
  splitEvidenceReason,
} from "@shadeshift/contracts";

type CellQuery = {
  eligibleOnly?: boolean;
  evidenceGrade?: EvidenceGrade;
  minPriority?: number;
  bbox?: [number, number, number, number];
};

type ArtifactInfo = {
  filename: string;
  path: string;
  sha256: string;
  enhanced: boolean;
};

@Injectable()
export class EvidenceService implements OnModuleInit {
  private cells!: RawPlanningCells;
  private topPriorities: EnhancedPriorityRecord[] = [];
  private highConfidencePriorities: EnhancedPriorityRecord[] = [];
  private artifacts: Record<string, ArtifactInfo> = {};
  private featureById = new Map<string, RawCellFeature>();

  onModuleInit() {
    const dataDir =
      process.env.SHADE_SHIFT_DATA_DIR ??
      resolve(process.cwd(), "../../../public/data");

    const cellsPath = this.pickExisting(dataDir, [
      "planning_cells_evidence_enhanced.geojson",
      "planning_cells.geojson",
    ]);

    const topPath = this.pickExisting(dataDir, [
      "priority_top10_evidence_enhanced.json",
      "priority_top10.json",
    ]);

    const strongPath = this.pickExisting(dataDir, [
      "high_confidence_priority_top10.json",
    ], false);

    if (!cellsPath || !topPath) {
      throw new ServiceUnavailableException(
        `ShadeShift data artifacts are missing under ${dataDir}. ` +
          `Expected planning_cells_evidence_enhanced.geojson and ` +
          `priority_top10_evidence_enhanced.json.`,
      );
    }

    this.cells = RawPlanningCellsSchema.parse(this.readJson(cellsPath));
    this.topPriorities = this.parsePriorityList(topPath);
    this.highConfidencePriorities = strongPath
      ? this.parsePriorityList(strongPath)
      : [];

    this.artifacts.cells = this.describeArtifact(
      cellsPath,
      cellsPath.endsWith("planning_cells_evidence_enhanced.geojson"),
    );
    this.artifacts.top = this.describeArtifact(
      topPath,
      topPath.endsWith("priority_top10_evidence_enhanced.json"),
    );
    if (strongPath) {
      this.artifacts.strongTop = this.describeArtifact(strongPath, true);
    }

    this.featureById = new Map(
      this.cells.features.map((feature) => [
        feature.properties.cell_id,
        feature,
      ]),
    );

    this.assertCrossFileConsistency();
    this.logStartupSummary(dataDir);
  }

  health() {
    return {
      status: "ok",
      cellsLoaded: this.cells.features.length,
      enhanced:
        this.artifacts.cells?.enhanced === true &&
        this.artifacts.top?.enhanced === true,
    };
  }

  getMeta(): MetaDto {
    const eligible = this.cells.features.filter(
      (f) => f.properties.eligible,
    );

    const evidenceGrades = eligible.reduce<Record<string, number>>(
      (acc, feature) => {
        const grade = feature.properties.evidence_grade ?? "ungraded";
        acc[grade] = (acc[grade] ?? 0) + 1;
        return acc;
      },
      {},
    );

    return {
      scienceRevision: "Gate C4.1 / C4-v3 spatial fix",
      productRevision: "product-v0.1",
      totalCells: this.cells.features.length,
      eligibleCells: eligible.length,
      evidenceGrades,
      artifacts: Object.fromEntries(
        Object.entries(this.artifacts).map(([key, value]) => [
          key,
          {
            filename: value.filename,
            sha256: value.sha256,
            enhanced: value.enhanced,
          },
        ]),
      ),
      semantics: {
        priority:
          "Relative investigation priority within the frozen pilot AOI; not a risk probability.",
        heat:
          "Median of per-date 500 m within-AOI daytime Landsat heat percentile ranks.",
        evidenceGrade:
          "Product-facing evidence-strength tier; it does not alter priority score or rank.",
        ecostressRole:
          "Context-only nighttime NASA observation layer; not a core ranking input.",
      },
    };
  }

  getCells(query: CellQuery): CellMapFeatureCollectionDto {
    const features = this.cells.features
      .filter((feature) => this.matchesQuery(feature, query))
      .map((feature) => this.toMapFeature(feature));

    return {
      type: "FeatureCollection",
      features,
    };
  }

  getCell(cellId: string): CellDetailDto {
    const feature = this.featureById.get(cellId);
    if (!feature) {
      throw new NotFoundException(`Unknown planning cell: ${cellId}`);
    }
    return this.toCellDetail(feature);
  }

  getTopPriorities(
    limit = 10,
    strongEvidenceOnly = false,
  ): PriorityListItemDto[] {
    const source =
      strongEvidenceOnly && this.highConfidencePriorities.length > 0
        ? this.highConfidencePriorities
        : this.topPriorities;

    return source
      .slice(0, Math.max(1, Math.min(limit, 50)))
      .map((record) => this.toPriorityListItem(record));
  }

  getMethodology(): MethodologyDto {
    return {
      question:
        "Within this ~14.7 km² Thủ Đức pilot, which 500 m cells are most useful to investigate first when persistent daytime heat and limited vegetation are considered together?",
      priorityFormula:
        "priority = 0.60 × validated daytime heat rank + 0.40 × current greening need",
      heatDefinition:
        "Each pre-selected Landsat 8/9 core date is aggregated to 500 m, ranked within the spatially supported pilot, then combined using the median percentile rank across usable dates.",
      greeningDefinition:
        "Greening need is the reliable built share relative to built + vegetation within each terrestrial planning cell.",
      evidenceDefinition:
        "Evidence grades summarize temporal stability, same-date stricter-QA corroboration, and spatial footprint support. They describe how well-supported a cell is; they never alter its priority rank.",
      historicalRole:
        "Reliable 2017→2025 vegetation-to-built change is explanatory support only. It can help interpret a cell, but it is never added to the core priority score.",
      ecostressRole:
        "NASA ECOSTRESS nighttime observations remain contextual evidence only because their hotspot pattern did not pass the project's temporal-persistence validation.",
      limitations: [
        "The score is relative to the frozen pilot AOI and is not a calibrated heat-health risk probability.",
        "Some cells have fewer usable Landsat dates; the product exposes scene count and temporal stability separately.",
        "Partial-edge cells are explicitly marked with footprint overlap and require sufficient spatial support for ranking.",
        "The land-cover classifier was validated against a weak multi-source consensus protocol, not independent human ground truth.",
      ],
    };
  }

  getLayers(): LayerDefinitionDto[] {
    return [
      {
        id: "priority",
        label: "Priority",
        field: "priorityScore",
        description:
          "Combined investigation priority from heat persistence and greening need.",
      },
      {
        id: "heat",
        label: "Day Heat",
        field: "heatScore",
        description:
          "Validated multi-date daytime Landsat relative heat rank.",
      },
      {
        id: "greening",
        label: "Greening Need",
        field: "greeningNeed",
        description:
          "Built dominance relative to vegetation among reliable terrestrial pixels.",
      },
      {
        id: "evidence",
        label: "Evidence",
        field: "evidenceGrade",
        description:
          "Evidence-strength grade derived from temporal, QA, and spatial support.",
      },
    ];
  }

  private parsePriorityList(path: string): EnhancedPriorityRecord[] {
    const parsed = this.readJson(path);
    const result = EnhancedPriorityListSchema.safeParse(parsed);

    if (!result.success) {
      throw new ServiceUnavailableException(
        `Priority artifact ${path} does not match the enhanced C4.1 contract: ${result.error.message}`,
      );
    }

    return result.data;
  }

  private toMapFeature(feature: RawCellFeature): CellMapFeatureDto {
    const p = feature.properties;
    return {
      type: "Feature",
      geometry: feature.geometry,
      properties: {
        cellId: p.cell_id,
        eligible: p.eligible,
        priorityRank: p.priority_rank,
        priorityScore: p.priority_core,
        heatScore: p.heat_score,
        greeningNeed: p.greening_need,
        evidenceGrade: p.evidence_grade === "unranked" ? null : (p.evidence_grade ?? null),
        evidenceCoverage: p.evidence_coverage_score,
        footprintOverlap: p.footprint_overlap_fraction,
        heatSceneCount: p.heat_scene_count,
        hotRecurrence: p.hot_recurrence,
      },
    };
  }

  private toCellDetail(feature: RawCellFeature): CellDetailDto {
    const p = feature.properties;

    return {
      cellId: p.cell_id,
      geometry: feature.geometry,
      priority: {
        rank: p.priority_rank,
        score: p.priority_core,
        eligible: p.eligible,
        highConfidenceRank: p.high_confidence_priority_rank ?? null,
      },
      heat: {
        score: p.heat_score,
        sceneCount: p.heat_scene_count,
        sceneFraction: p.heat_scene_fraction,
        hotRecurrence: p.hot_recurrence,
        rankIqr: p.heat_rank_iqr,
        guardedScore: p.guarded_heat_score,
        guardedSceneCount: p.guarded_scene_count,
        legacyQaGap: p.qa_tier_heat_gap,
        looMedianRange: p.heat_loo_median_range ?? null,
        pairedQaSceneCount: p.paired_qa_scene_count ?? null,
        pairedQaConsensusGap: p.paired_qa_consensus_gap ?? null,
        partialValidationCount: p.partial_validation_count ?? null,
        partialValidationMedianGap:
          p.partial_validation_median_gap ?? null,
      },
      landCover: {
        greeningNeed: p.greening_need,
        builtFraction: p.built_fraction_terrestrial,
        vegetationFraction: p.vegetation_fraction_terrestrial,
        waterFractionKnown: p.water_fraction_known,
        terrestrialShareOfKnown: p.terrestrial_share_of_known,
      },
      historical: {
        vegetationToBuiltFractionJointReliable:
          p.historical_v2b_fraction_joint_reliable,
      },
      evidence: {
        grade: p.evidence_grade === "unranked" ? null : (p.evidence_grade ?? null),
        temporalStrength: p.temporal_evidence_strength ?? null,
        qaStrength: p.qa_corroboration_strength ?? null,
        spatialStrength: p.spatial_evidence_strength ?? null,
        coverage: p.evidence_coverage_score,
        footprintOverlap: p.footprint_overlap_fraction,
        caveats: splitCaveats(p.evidence_caveats),
      },
      reason: splitEvidenceReason(p.evidence_reason),
    };
  }

  private toPriorityListItem(
    record: EnhancedPriorityRecord,
  ): PriorityListItemDto {
    return {
      cellId: record.cell_id,
      priorityRank: record.priority_rank,
      priorityScore: record.priority_core,
      heatScore: record.heat_score,
      greeningNeed: record.greening_need,
      evidence: {
        grade: record.evidence_grade,
        temporalStrength: record.temporal_evidence_strength,
        qaStrength: record.qa_corroboration_strength,
        spatialStrength: record.spatial_evidence_strength,
        coverage: record.evidence_coverage_score,
        footprintOverlap: record.footprint_overlap_fraction,
        caveats: splitCaveats(record.evidence_caveats),
      },
      heatSceneCount: record.heat_scene_count,
      heatLooMedianRange: record.heat_loo_median_range,
      pairedQaConsensusGap: record.paired_qa_consensus_gap,
      partialValidationCount: record.partial_validation_count,
      partialValidationMedianGap: record.partial_validation_median_gap,
      reason: splitEvidenceReason(record.evidence_reason),
      ...(record.high_confidence_priority_rank
        ? {
            highConfidencePriorityRank:
              record.high_confidence_priority_rank,
          }
        : {}),
    };
  }

  private matchesQuery(feature: RawCellFeature, query: CellQuery) {
    const p = feature.properties;

    if (query.eligibleOnly && !p.eligible) return false;
    if (query.evidenceGrade && p.evidence_grade !== query.evidenceGrade) {
      return false;
    }
    if (
      query.minPriority !== undefined &&
      (p.priority_core === null || p.priority_core < query.minPriority)
    ) {
      return false;
    }
    if (query.bbox && !this.geometryIntersectsBbox(feature, query.bbox)) {
      return false;
    }

    return true;
  }

  private geometryIntersectsBbox(
    feature: RawCellFeature,
    bbox: [number, number, number, number],
  ) {
    const [minX, minY, maxX, maxY] = bbox;
    const coords: [number, number][] = [];

    const collect = (value: unknown) => {
      if (
        Array.isArray(value) &&
        value.length >= 2 &&
        typeof value[0] === "number" &&
        typeof value[1] === "number"
      ) {
        coords.push([value[0] as number, value[1] as number]);
        return;
      }
      if (Array.isArray(value)) value.forEach(collect);
    };

    collect(feature.geometry.coordinates);
    if (!coords.length) return false;

    const xs = coords.map((c) => c[0]);
    const ys = coords.map((c) => c[1]);

    return !(
      Math.max(...xs) < minX ||
      Math.min(...xs) > maxX ||
      Math.max(...ys) < minY ||
      Math.min(...ys) > maxY
    );
  }

  private assertCrossFileConsistency() {
    const topIds = new Set<string>();

    for (const record of this.topPriorities) {
      if (topIds.has(record.cell_id)) {
        throw new ServiceUnavailableException(
          `Duplicate Top-10 cell: ${record.cell_id}`,
        );
      }
      topIds.add(record.cell_id);

      const feature = this.featureById.get(record.cell_id);
      if (!feature) {
        throw new ServiceUnavailableException(
          `Top-priority cell ${record.cell_id} is absent from planning GeoJSON.`,
        );
      }

      const p = feature.properties;
      this.assertClose(
        record.priority_core,
        p.priority_core,
        record.cell_id,
        "priority_core",
      );
      this.assertClose(
        record.heat_score,
        p.heat_score,
        record.cell_id,
        "heat_score",
      );
      this.assertClose(
        record.greening_need,
        p.greening_need,
        record.cell_id,
        "greening_need",
      );

      if (p.priority_rank !== record.priority_rank) {
        throw new ServiceUnavailableException(
          `Rank mismatch for ${record.cell_id}: top=${record.priority_rank}, geojson=${p.priority_rank}`,
        );
      }
    }

    for (const record of this.highConfidencePriorities) {
      if (!this.featureById.has(record.cell_id)) {
        throw new ServiceUnavailableException(
          `High-confidence cell ${record.cell_id} is absent from planning GeoJSON.`,
        );
      }
      if (record.evidence_grade !== "A") {
        throw new ServiceUnavailableException(
          `High-confidence list contains non-A cell ${record.cell_id}.`,
        );
      }
    }
  }

  private assertClose(
    expected: number,
    actual: number | null,
    cellId: string,
    field: string,
  ) {
    if (actual === null || Math.abs(expected - actual) > 1e-9) {
      throw new ServiceUnavailableException(
        `${field} mismatch for ${cellId}: top=${expected}, geojson=${actual}`,
      );
    }
  }

  private pickExisting(
    dataDir: string,
    filenames: string[],
    required = true,
  ): string | null {
    for (const filename of filenames) {
      const path = resolve(dataDir, filename);
      if (existsSync(path)) return path;
    }
    if (required) return null;
    return null;
  }

  private readJson(path: string): unknown {
    return JSON.parse(readFileSync(path, "utf-8"));
  }

  private sha256(path: string) {
    return createHash("sha256")
      .update(readFileSync(path))
      .digest("hex");
  }

  private describeArtifact(path: string, enhanced: boolean): ArtifactInfo {
    return {
      filename: path.split(/[\\/]/).pop() ?? path,
      path,
      sha256: this.sha256(path),
      enhanced,
    };
  }

  private logStartupSummary(dataDir: string) {
    const meta = this.getMeta();
    console.log("ShadeShift artifact contract validated.");
    console.log(`Data directory: ${dataDir}`);
    console.log(
      `Cells: ${meta.totalCells} total / ${meta.eligibleCells} eligible`,
    );
    const enhancedEvidence =
      this.artifacts.cells?.enhanced === true &&
      this.artifacts.top?.enhanced === true;

    console.log(`Enhanced evidence: ${enhancedEvidence}`);
  }
}
