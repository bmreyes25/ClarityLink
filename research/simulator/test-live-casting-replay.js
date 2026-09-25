const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const twin = require('./digital-twin');

const events = twin.parseJSONL(fs.readFileSync(path.join(__dirname, 'sample-live-casting-20260925.jsonl'), 'utf8'));
let state = twin.blank();
for (const event of events) {
  state = twin.apply(state, event);
  if (event.tMs === 12) {
    assert.equal(state.clusterCaptureId, 'cluster-20260925-native');
    assert.equal(state.centerCaptureId, 'center-20260925-native-maps');
  }
  if (event.tMs === 23) {
    assert.equal(state.display, 'casting');
    assert.equal(state.clusterCaptureId, 'cluster-20260925-cast-maps');
    assert.equal(state.centerCaptureId, 'center-20260925-cast-maps');
    assert.equal(state.voiceGuidance, 'heard');
  }
  if (event.tMs === 32) {
    assert.equal(state.centerApp, 'music');
    assert.equal(state.centerCaptureId, 'center-20260925-music');
    assert.equal(state.clusterCaptureId, 'cluster-20260925-cast-music');
    assert.equal(state.clusterStream.active, false);
  }
}
for (const name of ['center-20260925-native-maps.png', 'cluster-20260925-native.png',
                    'center-20260925-cast-maps.png', 'cluster-20260925-cast-maps.png', 'center-20260925-music.png',
                    'cluster-20260925-cast-music.png']) {
  assert.ok(fs.statSync(path.join(__dirname, 'assets', name)).size > 1000);
}
console.log('Live casting replay: native compass, Maps mirror, Music mirror, and voice observation passed.');
