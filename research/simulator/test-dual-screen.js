const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const twin = require('./digital-twin');

const events = twin.parseJSONL(fs.readFileSync(path.join(__dirname, 'sample-dual-screen.jsonl'), 'utf8'));
let state = twin.blank();
for (const event of events) {
  state = twin.apply(state, event);
  if (event.tMs === 8) {
    assert.equal(state.centerApp, 'music');
    assert.equal(state.clusterStream.active, true);
    assert.equal(state.clusterStream.frameId, 'map-002');
    assert.equal(state.clusterStream.frames, 2);
  }
  if (event.tMs === 9) {
    assert.equal(state.clusterStream.active, false);
    assert.equal(state.clusterStream.frameId, null);
  }
}
assert.equal(state.connected, false);
assert.deepEqual(state.clusterStream, twin.blank().clusterStream);

let noCluster = twin.apply(twin.blank(), {tMs: 0, type: 'connected'});
noCluster = twin.apply(noCluster, {tMs: 1, type: 'receiver-capabilities', clusterDisplay: false});
assert.throws(() => twin.apply(noCluster, {tMs: 2, type: 'cluster-setup'}), /advertised/);
assert.throws(() => twin.apply(noCluster, {tMs: 2, type: 'cluster-frame', frameId: 'x'}), /active/);
assert.throws(() => twin.apply(noCluster, {tMs: 2, type: 'center-app', app: 'invalid'}), /Invalid center/);

console.log('Dual-screen state model: independent center/cluster, capability gate, route end, and disconnect passed.');
