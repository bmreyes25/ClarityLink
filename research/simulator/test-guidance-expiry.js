const assert = require('node:assert/strict');
const twin = require('./digital-twin');

let state = twin.apply(twin.blank(), {tMs: 0, type: 'connected'});
state = twin.apply(state, {tMs: 1, type: 'guidance', maneuver: 'right', road: 'Synthetic Rd',
  distanceMeters: 300, sourceKind: 'route-metadata', provenance: 'hypothetical metadata fixture'});
state = twin.apply(state, {tMs: 5000, type: 'center-app', app: 'music'});
assert.equal(state.navigation.road, 'Synthetic Rd');
state = twin.apply(state, {tMs: 15002, type: 'vehicle', speedKph: 0});
assert.equal(state.navigation, null);

state = twin.apply(state, {tMs: 16000, type: 'guidance', maneuver: 'left', road: 'OCR Rd',
  distanceMeters: 100, sourceKind: 'center-ocr', provenance: 'center screenshot'});
state = twin.apply(state, {tMs: 16001, type: 'center-app', app: 'music'});
assert.equal(state.navigation, null);

console.log('Guidance expiry: metadata TTL and immediate center-OCR source loss passed.');
