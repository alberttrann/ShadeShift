// ShadeShift Gate B candidate-label generator + visual review layers.
// Candidate labels come from ESA WorldCover 2021 ONLY as a sampling hint.
// They are NOT ground truth until manually reviewed.

var aoi = ee.Geometry.Rectangle([106.715, 10.785, 106.755, 10.815]);
Map.centerObject(aoi, 14);

var wc = ee.ImageCollection('ESA/WorldCover/v200').first().select('Map');
// ShadeShift labels: 1 vegetation, 2 built, 3 bare_other, 4 water, 0 ignore.
// Vegetation candidate pool: tree, shrub, grass, cropland, wetland, mangrove.
var candidate = wc.remap(
  [10,20,30,40,90,95,50,60,80],
  [ 1, 1, 1, 1, 1, 1, 2, 3, 4], 0
).rename('candidate_label');

function maskS2(img) {
  var scl = img.select('SCL');
  var ok = scl.neq(3)  // cloud shadow
    .and(scl.neq(8))   // medium cloud
    .and(scl.neq(9))   // high cloud
    .and(scl.neq(10))  // cirrus
    .and(scl.neq(11)); // snow/ice
  return img.updateMask(ok);
}
function s2Composite(start, end) {
  return ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(aoi).filterDate(start,end).map(maskS2).median().clip(aoi);
}
var s2_2025 = s2Composite('2025-01-01','2026-01-01');
var s2_2017 = s2Composite('2017-01-01','2018-01-01');
var vis = {bands:['B4','B3','B2'], min:200, max:3000};
Map.addLayer(s2_2017, vis, 'Sentinel-2 2017 median', false);
Map.addLayer(s2_2025, vis, 'Sentinel-2 2025 median', true);
Map.addLayer(candidate, {min:1,max:4,palette:['2E8B57','B22222','C2B280','1E90FF']}, 'WorldCover candidate class', false);

var points = candidate.stratifiedSample({
  numPoints: 55,
  classBand: 'candidate_label',
  region: aoi,
  scale: 10,
  classValues: [1,2,3,4],
  classPoints: [55,55,55,55],
  seed: 42,
  geometries: true,
  tileScale: 4
});

points = points.map(function(f) {
  var xy=f.geometry().coordinates();
  return f.set({
    lon: xy.get(0), lat: xy.get(1),
    manual_label: 0,
    verified: 0,
    reference_year: 2025,
    reference_source: 'manual_visual_review_required',
    stable_2017: 0,
    label_2017: 0,
    review_confidence: '',
    notes: ''
  });
});

print('Candidate counts by hint class', points.aggregate_histogram('candidate_label'));
Map.addLayer(points, {color:'yellow'}, 'Candidate points', true);

Export.table.toDrive({
  collection: points,
  description: 'shadeshift_gate_b_candidate_labels',
  fileNamePrefix: 'shadeshift_gate_b_candidate_labels',
  fileFormat: 'GeoJSON'
});
