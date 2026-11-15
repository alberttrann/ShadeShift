import "reflect-metadata";
import { NestFactory } from "@nestjs/core";
import { DocumentBuilder, SwaggerModule } from "@nestjs/swagger";
import { AppModule } from "./app.module";

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  app.setGlobalPrefix("api/v1");

  const allowedOrigins = (
    process.env.WEB_ORIGIN ?? "http://localhost:3000"
  )
    .split(",")
    .map((origin) => origin.trim())
    .filter(Boolean);

  app.enableCors({
    origin: allowedOrigins,
    methods: ["GET"],
  });

  const swaggerConfig = new DocumentBuilder()
    .setTitle("ShadeShift Evidence API")
    .setDescription(
      "Read-only API over frozen ShadeShift planning evidence artifacts.",
    )
    .setVersion("1.0.0")
    .build();

  const document = SwaggerModule.createDocument(app, swaggerConfig);
  SwaggerModule.setup("docs", app, document);

  const port = Number(process.env.PORT ?? 4000);

  // Railway expects services to listen on its injected PORT and 0.0.0.0.
  await app.listen(port, "0.0.0.0");

  console.log(`ShadeShift API listening on 0.0.0.0:${port}`);
  console.log(`Health:  /api/v1/health`);
  console.log(`Swagger: /docs`);
}

bootstrap();
