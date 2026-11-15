import { Module } from "@nestjs/common";
import { EvidenceModule } from "./evidence/evidence.module";

@Module({
  imports: [EvidenceModule],
})
export class AppModule {}
