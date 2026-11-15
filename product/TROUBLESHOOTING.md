# ShadeShift Product Troubleshooting

## `EUNSUPPORTEDPROTOCOL workspace:*`

Cause: the local npm client does not accept the `workspace:*` dependency
specifier used by the first starter.

Fixed in v0.1.1 by using:

`file:../../packages/contracts`

for both the API and web apps.

## `'tsc' is not recognized`

Do not install TypeScript globally as the first reaction.

In the reported failure this occurs because the preceding `npm install`
aborted before local dev dependencies were installed.

Run:

```powershell
.\repair_install.ps1
```

then:

```powershell
npm run dev
```

## Useful diagnostics

```powershell
node --version
npm --version
npm ls typescript
npm ls @shadeshift/contracts
```

After a successful install, the last two should resolve from the local project.
