const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const twin = require('./digital-twin');

const events = twin.parseJSONL(fs.readFileSync(path.join(__dirname, 'sample-waze-headunit-20260925.jsonl'), 'utf8'));
let state = twin.blank();
for (const event of events) {
  state = twin.apply(state, event);
  if (event.tMs === 22) {
    assert.equal(state.centerApp, 'home');
    assert.equal(state.centerCaptureId, 'center-20260925-honda-home');
    assert.equal(state.clusterCaptureId, 'cluster-20260925-waze-route');
  }
  if (event.tMs === 33) {
    assert.equal(state.centerApp, 'waze');
    assert.equal(state.clusterCaptureId, 'cluster-20260925-waze-ended');
  }
}
const asset = name => fs.readFileSync(path.join(__dirname, 'assets', name));
for (const name of ['center-20260925-waze-route.png', 'cluster-20260925-waze-route.png',
                    'center-20260925-honda-home.png', 'center-20260925-waze-ended.png',
                    'cluster-20260925-waze-ended.png']) assert.ok(asset(name).length > 1000);

const source = path.join(__dirname, '..', 'captures');
assert.deepEqual(asset('cluster-20260925-waze-route.png'),
  fs.readFileSync(path.join(source, '20260925-waze-background-home', 'twin-survey', 'display-1.png')));
assert.notDeepEqual(asset('cluster-20260925-waze-route.png'), asset('cluster-20260925-waze-ended.png'));
console.log('Head-unit Waze replay: guidance persists over Honda Home and clears at route end.');
