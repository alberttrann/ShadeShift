# ShadeShift Product

This directory contains the interactive ShadeShift evidence product.

For the **project story, scientific validation, data sources, and final findings**, read the repository root [`README.md`](../README.md).

## Product architecture

```text
apps/web        Next.js + MapLibre interface
apps/api        NestJS read-only evidence API
packages/contracts
                shared TypeScript/Zod contracts
scripts         product asset generation and verification
```

The application does **not** perform live satellite inference. It serves frozen, validated evidence artifacts produced by the science pipeline.

## Local development

```powershell
cd product
Copy-Item .env.example .env
npm install
npm run dev
```

Default services:

- Web: `http://localhost:3000`
- API: `http://localhost:4000/api/v1`
- Swagger: `http://localhost:4000/docs`

A MapTiler key is optional. Without one, the science layers can still run with the local analysis view.

## Derived classifier layers

If the source Gate-B rasters are available in the parent science workspace:

```powershell
npm run prepare:classifier-layers
npm run verify:classifier-context
```

This prepares:

- whole-pilot 10 m land-cover context;
- whole-pilot historical vegetation→built support;
- selected-cell land-cover and historical context layers.

These are explanatory visualizations. They do not recompute the frozen priority score.

## Type checks

```powershell
npm run build:contracts
npm exec -- tsc -p apps/web/tsconfig.json --noEmit
npm exec -- tsc -p apps/api/tsconfig.json --noEmit
```

## Product semantics

The interface preserves several deliberate scientific boundaries:

- Priority is a relative pilot-area investigation score.
- Evidence grade never changes priority rank.
- Historical vegetation→built change is support-only.
- ECOSTRESS is contextual only after failing the pilot persistence test.
- The 10 m classifier is land-cover evidence, not 10 m thermal information.
- The product is not a citywide heat-risk model or intervention prescription.
