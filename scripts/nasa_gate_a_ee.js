// ShadeShift Gate A: verify real NASA thermal coverage over the fixed HCMC pilot AOI.
// Paste into https://code.earthengine.google.com/ and Run.
// Gate A needs at least one NASA collection with >0 usable AOI observations.

var aoi = ee.Geometry.Rectangle([106.715, 10.785, 106.755, 10.815], null, false);
var start = '2025-02-01';
var end   = '2025-05-01';

Map.centerObject(aoi, 13);
Map.addLayer(aoi, {color: 'yellow'}, 'ShadeShift AOI');

// -------- ECOSTRESS 70 m --------
var ecoRaw = ee.ImageCollection('NASA/ECOSTRESS/L2T_LSTE/V2')
  .filterBounds(aoi)
  .filterDate(start, end);

function addEcoCoverage(img) {
  // Earth Engine catalog: cloud bit 0 == 0 is clear; QC bit 0 == 0 is good LST quality.
  // Use the dedicated cloud band rather than assuming V1 cloud semantics inside QC.
  var clear = img.select('cloud').bitwiseAnd(1).eq(0);
  var goodLst = img.select('QC').bitwiseAnd(1).eq(0);
  var produced = img.select('LST').gt(0);
  var land = img.select('water').bitwiseAnd(1).eq(0);
  var valid = clear.and(goodLst).and(produced).and(land).rename('valid');

  var stats = valid.reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: aoi,
    scale: 70,
    bestEffort: true,
    maxPixels: 1e7
  });
  var fraction = ee.Number(ee.Dictionary(stats).get('valid', 0));
  return img.set({
    valid_fraction: fraction,
    acquisition_utc: img.date().format('YYYY-MM-dd HH:mm:ss'),
    acquisition_millis: img.date().millis()
  });
}

var eco = ecoRaw.map(addEcoCoverage);
var ecoUsable = eco.filter(ee.Filter.gt('valid_fraction', 0.05));
var ecoTable = ee.FeatureCollection(ecoUsable.map(function(img) {
  return ee.Feature(null, {
    id: img.id(),
    acquisition_utc: img.get('acquisition_utc'),
    valid_fraction: img.get('valid_fraction')
  });
})).sort('valid_fraction', false);

print('ECOSTRESS intersecting images, Feb-Apr 2025', ecoRaw.size());
print('ECOSTRESS usable images (>5% clear/good/land AOI)', ecoUsable.size());
print('ECOSTRESS usable scenes sorted by valid coverage', ecoTable.limit(25));

var bestEco = ee.Image(ecoUsable.sort('valid_fraction', false).first());
var hasEco = ecoUsable.size().gt(0);
var ecoLSTC = ee.Image(ee.Algorithms.If(
  hasEco,
  bestEco.select('LST').subtract(273.15),
  ee.Image.constant(0).updateMask(ee.Image.constant(0))
));
Map.addLayer(ecoLSTC, {min: 20, max: 50, palette: ['blue','cyan','yellow','orange','red']}, 'Best ECOSTRESS LST °C');

// -------- MODIS fallback / independent coverage check --------
var modRaw = ee.ImageCollection('MODIS/061/MOD11A2')
  .filterBounds(aoi)
  .filterDate(start, end);

function addModCoverage(img) {
  // QC_Day bits 0-1 == 00 => mandatory QA good quality.
  var good = img.select('QC_Day').bitwiseAnd(3).eq(0)
    .and(img.select('LST_Day_1km').gt(0))
    .rename('valid');
  var stats = good.reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: aoi,
    scale: 1000,
    bestEffort: true,
    maxPixels: 1e6
  });
  var fraction = ee.Number(ee.Dictionary(stats).get('valid', 0));
  return img.set({
    valid_fraction: fraction,
    acquisition_utc: img.date().format('YYYY-MM-dd')
  });
}

var mod = modRaw.map(addModCoverage);
var modUsable = mod.filter(ee.Filter.gt('valid_fraction', 0));
print('MODIS MOD11A2 intersecting composites, Feb-Apr 2025', modRaw.size());
print('MODIS usable composites (>0 good AOI coverage)', modUsable.size());
print('MODIS coverage table', ee.FeatureCollection(modUsable.map(function(img) {
  return ee.Feature(null, {
    id: img.id(),
    acquisition_utc: img.get('acquisition_utc'),
    valid_fraction: img.get('valid_fraction')
  });
})).sort('valid_fraction', false));

// Gate A interpretation:
// PASS NASA sub-gate if either ECOSTRESS usable images > 0 OR MODIS usable composites > 0.
// Prefer ECOSTRESS for the eventual local heat layer; MODIS is fallback/context only.
