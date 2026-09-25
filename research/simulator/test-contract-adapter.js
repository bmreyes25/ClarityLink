const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const twin = require('./digital-twin');
const {validate} = require('../contracts/validate-cluster-stream');
const {adapt} = require('./contract-adapter');

const text = fs.readFileSync(path.join(__dirname, '../contracts/cluster-stream-center-music.jsonl'), 'utf8');
assert.equal(validate(text).streams, 1);
const mapped = adapt(twin.parseJSONL(text));
assert.equal(mapped.filter(e => e.type === 'cluster-frame').length, 2);
const replayText = fs.readFileSync(path.join(__dirname, 'sample-contract-replay.jsonl'), 'utf8');
const replayEvents = twin.parseJSONL(replayText);
let state = twin.blank();
for (const event of replayEvents) {
  state = twin.apply(state, event);
  if (event.type === 'cluster-frame' && event.frameId === 'cluster-0001') {
    assert.equal(state.centerApp, 'music');
    assert.equal(state.clusterStream.active, true);
    assert.equal(state.clusterStream.frameId, 'cluster-0001');
  }
  if (event.type === 'cluster-stop') {
    assert.equal(state.clusterStream.active, false);
    assert.equal(state.clusterStream.frameId, null);
  }
}
assert.equal(state.connected, false);
assert.deepEqual(state.clusterStream, twin.blank().clusterStream);
assert.throws(() => adapt([{type: 'frame-ready', atMs: 0, frameRef: 'file:///bad'}]), /bench frame/);
console.log('Contract adapter: bench frame survives center Music and clears on stop/disconnect.');
