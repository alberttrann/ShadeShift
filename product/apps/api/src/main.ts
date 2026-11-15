import "reflect-metadata";
import { NestFactory } from "@nestjs/core";
import { DocumentBuilder, SwaggerModule } from "@nestjs/swagger";
import { AppModule } from "./app.module";

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  app.setGlobalPrefix("api/v1");
  app.enableCors({
    origin: process.env.WEB_ORIGIN ?? "http://localhost:3000",
    methods: ["GET"],
  });

  const swaggerConfig = new DocumentBuilder()
    .setTitle("ShadeShift Evidence API")
    .setDescription(
      "Read-only API over frozen ShadeShift planning evidence artifacts.",
    )
    .setVersion("0.1.0")
    .build();

  const document = SwaggerModule.createDocument(app, swaggerConfig);
  SwaggerModule.setup("docs", app, document);

  const port = Number(process.env.PORT ?? 4000);
  await app.listen(port);

  console.log(`ShadeShift API: http://localhost:${port}/api/v1`);
  console.log(`Swagger:        http://localhost:${port}/docs`);
}

bootstrap();
