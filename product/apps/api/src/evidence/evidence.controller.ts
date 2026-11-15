import {
  BadRequestException,
  Controller,
  Get,
  Param,
  Query,
} from "@nestjs/common";
import {
  ApiOkResponse,
  ApiOperation,
  ApiParam,
  ApiQuery,
  ApiTags,
} from "@nestjs/swagger";
import { EvidenceGrade } from "@shadeshift/contracts";
import { EvidenceService } from "./evidence.service";

@ApiTags("ShadeShift")
@Controller()
export class EvidenceController {
  constructor(private readonly evidence: EvidenceService) {}

  @Get("health")
  @ApiOperation({ summary: "Health and artifact-load status" })
  health() {
    return this.evidence.health();
  }

  @Get("meta")
  @ApiOperation({ summary: "Science/product metadata and artifact hashes" })
  getMeta() {
    return this.evidence.getMeta();
  }

  @Get("cells")
  @ApiOperation({ summary: "Map-ready planning cells as GeoJSON" })
  @ApiQuery({ name: "eligible", required: false, example: "true" })
  @ApiQuery({ name: "evidenceGrade", required: false, enum: ["A", "B", "C"] })
  @ApiQuery({ name: "minPriority", required: false, example: "0.7" })
  @ApiQuery({
    name: "bbox",
    required: false,
    example: "106.72,10.79,106.75,10.81",
  })
  getCells(
    @Query("eligible") eligible?: string,
    @Query("evidenceGrade") evidenceGrade?: string,
    @Query("minPriority") minPriority?: string,
    @Query("bbox") bbox?: string,
  ) {
    const grade = this.parseGrade(evidenceGrade);
    return this.evidence.getCells({
      eligibleOnly: eligible === "true",
      evidenceGrade: grade,
      minPriority:
        minPriority !== undefined
          ? this.parseFiniteNumber(minPriority, "minPriority")
          : undefined,
      bbox: bbox ? this.parseBbox(bbox) : undefined,
    });
  }

  @Get("cells/:cellId")
  @ApiOperation({ summary: "Detailed evidence for one planning cell" })
  @ApiParam({ name: "cellId", example: "C025" })
  getCell(@Param("cellId") cellId: string) {
    return this.evidence.getCell(cellId);
  }

  @Get("priorities/top")
  @ApiOperation({ summary: "Priority shortlist" })
  @ApiQuery({ name: "limit", required: false, example: 10 })
  @ApiQuery({
    name: "strongEvidenceOnly",
    required: false,
    example: "false",
  })
  getTop(
    @Query("limit") limit?: string,
    @Query("strongEvidenceOnly") strongEvidenceOnly?: string,
  ) {
    const parsedLimit =
      limit !== undefined
        ? Math.floor(this.parseFiniteNumber(limit, "limit"))
        : 10;

    return this.evidence.getTopPriorities(
      parsedLimit,
      strongEvidenceOnly === "true",
    );
  }

  @Get("methodology")
  @ApiOperation({ summary: "Human-readable methodology and limitations" })
  getMethodology() {
    return this.evidence.getMethodology();
  }

  @Get("layers")
  @ApiOperation({ summary: "Supported map visualization modes" })
  getLayers() {
    return this.evidence.getLayers();
  }

  private parseGrade(value?: string): EvidenceGrade | undefined {
    if (!value) return undefined;
    if (value === "A" || value === "B" || value === "C") return value;
    throw new BadRequestException("evidenceGrade must be A, B, or C");
  }

  private parseFiniteNumber(value: string, field: string) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
      throw new BadRequestException(`${field} must be a finite number`);
    }
    return parsed;
  }

  private parseBbox(value: string): [number, number, number, number] {
    const parts = value.split(",").map(Number);
    if (parts.length !== 4 || parts.some((x) => !Number.isFinite(x))) {
      throw new BadRequestException(
        "bbox must be minLon,minLat,maxLon,maxLat",
      );
    }
    const [minX, minY, maxX, maxY] = parts as [
      number,
      number,
      number,
      number,
    ];
    if (minX >= maxX || minY >= maxY) {
      throw new BadRequestException("bbox min values must be < max values");
    }
    return [minX, minY, maxX, maxY];
  }
}
