const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const twin = require('./digital-twin');
const {ABI, AndroidModel, ReceiverABIModel, replayRuntimeSnapshots} = require('./service-model');
const connected = () => { const model = new AndroidModel(); model.apply({tMs: 0, type: 'connected'}); return model; };
const setup = model => {
  for (const [tMs, type] of [[1, 'receiver-capabilities'], [2, 'cluster-setup'], [3, 'cluster-activate']])
    model.apply({tMs, type, clusterDisplay: true});
  model.apply({tMs: 4, type: 'cluster-frame', frameId: 'proposed-map'});
};

test('ABI singleton offsets and lifecycle are explicitly modeled, not ARM execution', () => {
  const receiver = new ReceiverABIModel();
  assert.equal(ABI.callbackBytes, 24); assert.deepEqual(Object.values(ABI.offsets), [0, 4, 8, 12, 16, 20]);
  assert.match(ABI.evidence, /ARM not executed/);
  assert.throws(() => receiver.callback('start'), /registration/);
  assert.equal(receiver.register(), 0); assert.equal(receiver.register(), 0x16);
  assert.throws(() => receiver.callback('initialize'), /transport/);
  receiver.attach(); receiver.callback('initialize');
  assert.throws(() => receiver.callback('processData', 'frame'), /running/);
  receiver.callback('setProperty', {width: 800, height: 480}); receiver.callback('start');
  receiver.callback('processData', 'frame'); assert.equal(receiver.display.frame, 'frame');
  receiver.callback('stop'); assert.equal(receiver.display.frame, null);
  assert.throws(() => receiver.callback('processData', 'late'), /running/);
  receiver.callback('finalize'); receiver.disconnect();
  assert.equal(receiver.usb.attached, false); assert.equal(receiver.mfi.ready, false);
  assert.equal(receiver.register(), 0);
});

test('modeled mirror follows Music while proposed independent map persists; audio state continuous', () => {
  const mirror = connected(), proposed = connected(); setup(proposed);
  for (const model of [mirror, proposed]) {
    model.apply({tMs: 5, type: 'display', mode: 'casting'});
    model.apply({tMs: 6, type: 'center-app', app: 'maps'});
    model.binder.call('Audio', 'update', {music: 'playing', voice: 'speaking'});
    const audio = {...model.receiver.audio};
    model.apply({tMs: 7, type: 'center-app', app: 'music'});
    assert.deepEqual(model.receiver.audio, audio);
    assert.equal(model.outputs.center, 'music');
  }
  assert.equal(mirror.outputs.hdmi, 'music');
  assert.equal(proposed.outputs.hdmi, 'synthetic:proposed-map');
});

test('mock Binder Honda guidance survives app switch and clears on end, TTL and disconnect', () => {
  const model = connected();
  const guidance = () => model.binder.call('Navigation', 'guidance', {maneuver: 'right', distanceMeters: 81});
  guidance(); model.apply({tMs: 1, type: 'center-app', app: 'home'});
  assert.equal(model.outputs.hdmi, 'modeled:honda-guidance');
  model.apply({tMs: 2, type: 'guidance-end'}); assert.equal(model.hondaGuidance, null);
  guidance(); model.apply({tMs: 15002, type: 'tick'}); assert.equal(model.hondaGuidance, null);
  guidance(); model.apply({tMs: 15003, type: 'disconnected'});
  assert.equal(model.hondaGuidance, null); assert.deepEqual(model.outputs, {center: null, hdmi: null});
  assert.throws(() => model.binder.call('Navigation', 'guidance', {maneuver: 'right', distanceMeters: 81}), /session/);
  assert.throws(() => model.binder.call('VehicleBus', 'send'), /Unmodeled/);
  assert.throws(() => model.binder.call('Navigation', 'factoryTBT'), /Unmodeled/);
});

test('proposed stream expires at boundary and rejects late frames until fresh setup', () => {
  const model = connected(); setup(model);
  model.apply({tMs: 15003, type: 'tick'}); assert.equal(model.state.clusterStream.frameId, 'proposed-map');
  model.apply({tMs: 15004, type: 'tick'}); assert.deepEqual(model.state.clusterStream, twin.blank().clusterStream);
  assert.throws(() => model.apply({tMs: 15005, type: 'cluster-frame', frameId: 'late'}), /active/);
  assert.equal(model.outputs.hdmi, null);
});

test('route end, stream failure, disconnect and reconnect release state without altering audio before disconnect', () => {
  for (const type of ['guidance-end', 'cluster-stop', 'disconnected', 'connected']) {
    const model = connected(); setup(model);
    model.binder.call('Audio', 'update', {music: 'playing', voice: 'idle'});
    const audio = {...model.receiver.audio}; model.apply({tMs: 8, type});
    assert.equal(model.state.clusterStream.frameId, null);
    assert.throws(() => model.apply({tMs: 9, type: 'cluster-frame', frameId: 'late'}), /active/);
    if (['guidance-end', 'cluster-stop'].includes(type)) assert.deepEqual(model.receiver.audio, audio);
    else assert.equal(model.receiver.audio.focus, null);
  }
});

test('observed mirror and Honda fixture replays use captured IDs; proposed fixture uses synthetic IDs', () => {
  for (const [name, checkTime, expected] of [
    ['sample-live-casting-20260925.jsonl', 32, 'cluster-20260925-cast-music'],
    ['sample-waze-headunit-20260925.jsonl', 22, 'cluster-20260925-waze-route'],
    ['sample-dual-screen.jsonl', 8, 'synthetic:map-002']]) {
    const model = new AndroidModel();
    for (const event of twin.parseJSONL(fs.readFileSync(path.join(__dirname, name), 'utf8'))) {
      model.apply(event);
      if (event.tMs === checkTime) assert.equal(model.outputs.hdmi, expected);
    }
  }
});

test('rejected events do not mutate Android resources or audio', () => {
  const model = connected(); const before = JSON.stringify(model);
  assert.throws(() => model.apply({tMs: 1, type: 'cluster-frame', frameId: 'bad'}), /active/);
  assert.equal(JSON.stringify(model), before);
  assert.throws(() => model.apply({tMs: -1, type: 'tick'}), /time/);
});

test('eight runtime snapshots drive inferred model lifecycle without inventing ABI or audio measurements', () => {
  const catalog = JSON.parse(fs.readFileSync(path.join(__dirname, 'firmware-catalog.json'), 'utf8'));
  const {model, checkpoints} = replayRuntimeSnapshots(catalog);
  assert.equal(checkpoints.length, 8);
  assert.equal(checkpoints[4].centerApp, 'music'); assert.equal(checkpoints[4].receiverPhase, 'running');
  for (const checkpoint of checkpoints) {
    assert.equal(checkpoint.audioFocus, null);
    assert.match(checkpoint.synthetic, /ABI calls/); assert.ok(checkpoint.files['audio.stdout.txt'].sha256);
  }
  assert.equal(model.receiver.usb.attached, false); assert.equal(model.receiver.display.frame, null);
  assert.throws(() => replayRuntimeSnapshots({runtimeSnapshots: [{state: 'invented'}]}), /Unknown/);
});
