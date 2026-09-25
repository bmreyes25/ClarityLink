const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const twin = require('./digital-twin');

const events = twin.parseJSONL(fs.readFileSync(path.join(__dirname, 'sample-captured-pair.jsonl'), 'utf8'));
let state = twin.blank();
for (const event of events) {
  state = twin.apply(state, event);
  if (event.tMs === 20) assert.equal(state.navigation.road, 'Example Road');
  if (event.tMs === 30) {
    assert.equal(state.centerCaptureId, 'center-music');
    assert.equal(state.clusterCaptureId, 'cluster-navigation');
    assert.equal(state.navigation, null);
  }
  if (event.tMs === 40) {
    assert.equal(state.navigation, null);
    assert.equal(state.centerCaptureId, null);
    assert.equal(state.clusterCaptureId, null);
  }
}
assert.throws(() => twin.apply(twin.blank(), {tMs: 1, type: 'capture-frame', display: 'center', captureId: 'center-maps'}), /connected/);
let connected = twin.apply(twin.blank(), {tMs: 0, type: 'connected'});
assert.throws(() => twin.apply(connected, {tMs: 1, type: 'capture-frame', display: 'center', captureId: '../secret'}), /capture/);
assert.throws(() => twin.apply(connected, {tMs: 1, type: 'capture-frame', display: 'cluster', captureId: 'center-music'}), /capture/);
assert.throws(() => twin.apply(connected, {tMs: 1, type: 'capture-frame', display: 'other', captureId: 'center-maps'}), /display/);
console.log('Captured pair replay: source frames, guidance clearing, disconnect cleanup, and invalid IDs passed.');
