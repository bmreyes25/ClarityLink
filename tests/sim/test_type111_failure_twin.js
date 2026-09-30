'use strict';
const assert = require('node:assert/strict');
const {Type111FailureTwin} = require('../../src/claritylink-sim/type111-failure-twin');

const stock = {streams: [
  {type: 100, dataPort: 5100, opaque: 'audio'},
  {type: 110, dataPort: 5200, streamConnectionID: 73, opaque: 'center'}
], vendorField: {preserve: true}};
assert.equal(Object.hasOwn(stock.streams[1], 'key'), false);
assert.equal(Object.hasOwn(stock.streams[1], 'iv'), false);
const readyTwin = () => {
  const twin = new Type111FailureTwin();
  twin.startSession(stock);
  twin.setAudio({centerActive: true, voiceRouteActive: true, focusOwner: 'synthetic-stock'});
  return twin;
};
const openSecondary = twin => {
  assert.equal(twin.requestType111({streamConnectionID: 91, dataPort: 6200}).ok, true);
  assert.equal(twin.connect().ok, true);
  assert.equal(twin.receiveHeader().ok, true);
  assert.equal(twin.receiveConfig().ok, true);
};
const primarySnapshot = twin => twin.snapshotPrimary();

const negotiationFailures = [
  ['missing-display', {streamConnectionID: 91}],
  ['unknown-display-correlation', {streamConnectionID: 91}],
  ['missing-response-field', {streamConnectionID: 91}],
  ['unsupported-skipped', {streamConnectionID: 91}],
  ['malformed-request', {streamConnectionID: 91}],
  ['dataPort-allocation', {streamConnectionID: 91}],
  ['bind', {streamConnectionID: 91}],
  ['listen', {streamConnectionID: 91}],
  ['crypto-derive', {streamConnectionID: 91}],
  ['bad-iv', {streamConnectionID: 91}],
  ['ctr-missing', {streamConnectionID: 91}]
];

for (const [stage, input] of negotiationFailures) {
  const twin = readyTwin();
  const before = primarySnapshot(twin);
  const result = twin.requestType111({...input, failAt: stage});
  assert.equal(result.ok, false, stage);
  assert.equal(primarySnapshot(twin), before, stage + ' mutated Type110/audio');
  assert.deepEqual(twin.type110.response, stock, stage + ' changed stock response');
  assert.equal(twin.type110.active, true, stage + ' stopped Type110');
}

{
  const twin = new Type111FailureTwin();
  assert.throws(() => twin.requestType111({streamConnectionID: 91}), /not connected/);
  assert.equal(twin.type110.active, false);
  twin.startSession(stock);
  const before = primarySnapshot(twin);
  assert.equal(twin.requestType111({}).stage, 'missing-stream-connection-id');
  assert.equal(twin.requestType111({streamConnectionID: 0}).stage, 'invalid-stream-connection-id');
  assert.equal(primarySnapshot(twin), before, 'missing/invalid ID changed Type110/audio');
  assert.equal(twin.requestType111({streamConnectionID: 91, dataPort: 70000}).ok, false);
  assert.equal(twin.type110.active, true);
  twin.disconnectType110();
  assert.equal(twin.requestType111({streamConnectionID: 91}).stage, 'type110-not-established');
}

{
  const twin = readyTwin();
  const before = primarySnapshot(twin);
  const result = twin.requestType111({
    streamConnectionID: 91,
    unknownFields: ['displayUUID-to-stream-ID-correlation']
  });
  assert.equal(result.ok, true);
  assert.equal(result.response.evidence, 'synthetic-hypothesis');
  assert.equal(Object.hasOwn(result.response, 'key'), false);
  assert.equal(Object.hasOwn(result.response, 'iv'), false);
  assert.equal(twin.type111.unknownFields.includes('Honda Type111 schema'), true);
  assert.equal(twin.type111.unknownFields.includes('displayUUID-to-stream-ID-correlation'), true);
  assert.equal(primarySnapshot(twin), before);
  const generation = twin.type111.generation;
  assert.equal(twin.requestType111({streamConnectionID: 92}).ok, false, 'duplicate Type111 accepted');
  assert.equal(primarySnapshot(twin), before);
  assert.equal(twin.type111.generation, generation, 'duplicate request replaced active generation');
  twin.disconnectType111();
  assert.equal(twin.requestType111({streamConnectionID: 93}).ok, true, 'reconnect did not allocate a new generation');
  assert.equal(twin.type111.generation, generation + 1);
}

const listenerFailures = [
  'accept-timeout', 'teardown-while-accepting',
  'disconnect-before-header', 'disconnect-mid-header'
];
for (const stage of listenerFailures) {
  const twin = readyTwin();
  twin.requestType111({streamConnectionID: 91});
  const before = primarySnapshot(twin);
  const result = stage.startsWith('disconnect') ? twin.receiveHeader({failAt: stage}) : twin.connect({failAt: stage});
  assert.equal(result.ok, false, stage);
  assert.equal(primarySnapshot(twin), before, stage + ' mutated primary');
  assert.equal(twin.type111.phase, 'idle', stage + ' leaked secondary state');
}

{
  const twin = readyTwin();
  twin.requestType111({streamConnectionID: 91}); twin.connect();
  const before = primarySnapshot(twin);
  assert.equal(twin.receiveHeader({valid: false}).ok, false, 'malformed 128-byte header accepted');
  assert.equal(primarySnapshot(twin), before, 'malformed header changed Type110/audio');
}

const configFailures = [
  'opcode1-before-key-ready', 'decrypt-failure', 'missing-video-config',
  'malformed-video-config', 'unsupported-nal-length', 'truncated-sps-pps'
];
for (const stage of configFailures) {
  const twin = readyTwin();
  twin.requestType111({streamConnectionID: 91}); twin.connect(); twin.receiveHeader();
  const before = primarySnapshot(twin);
  assert.equal(twin.receiveConfig({failAt: stage}).ok, false, stage);
  assert.equal(primarySnapshot(twin), before, stage + ' changed Type110 crypto/audio');
  assert.equal(twin.type111.phase, 'idle');
}

const frameFailures = [
  'opcode0-before-config', 'disconnect-mid-body', 'body-too-large',
  'truncated-avcc-nal', 'h264-extractor-error', 'unknown-opcode', 'decrypt-failure'
];
for (const stage of frameFailures) {
  const twin = readyTwin();
  twin.requestType111({streamConnectionID: 91}); twin.connect(); twin.receiveHeader();
  twin.receiveConfig();
  const before = primarySnapshot(twin);
  assert.equal(twin.receiveFrame({failAt: stage}).ok, false, stage);
  assert.equal(primarySnapshot(twin), before, stage + ' changed primary');
}

const rendererFailures = [
  'renderer-unavailable', 'renderer-bad-dimensions', 'renderer-timeout',
  'externaldisplay-host-unavailable', 'crop-mask-unknown', 'synthetic-frame-dropped'
];
for (const stage of rendererFailures) {
  const twin = readyTwin();
  openSecondary(twin); twin.receiveFrame();
  const before = primarySnapshot(twin);
  assert.equal(twin.submitFrame({failAt: stage}).ok, false, stage);
  assert.equal(primarySnapshot(twin), before, stage + ' changed Type110/audio');
  assert.equal(twin.type111.phase, 'idle');
}

{
  const twin = readyTwin();
  openSecondary(twin);
  twin.type110.cryptoCounter = 17;
  const primaryCrypto = twin.type110.cryptoCounter;
  const secondaryCrypto = twin.type111.ctrCounter;
  assert.notEqual(twin.type111, twin.type110);
  twin.receiveFrame();
  assert.equal(twin.type110.cryptoCounter, primaryCrypto, 'Type111 advanced Type110 CTR');
  assert.equal(twin.type111.ctrCounter, secondaryCrypto + 1);
  const before = primarySnapshot(twin);
  twin.disconnectType111();
  assert.equal(primarySnapshot(twin), before, 'secondary teardown changed primary/audio');
  assert.equal(twin.type111.phase, 'idle');
  assert.equal(twin.type110.active, true);
}

{
  const twin = readyTwin();
  openSecondary(twin);
  twin.disconnectType110();
  assert.equal(twin.type110.active, false);
  assert.equal(twin.type111.phase, 'idle', 'parent stream failure left child active');
  assert.equal(twin.audio.centerActive, true, 'Type110 stream-only loss rewrote session audio policy');
}

{
  const twin = readyTwin();
  openSecondary(twin);
  twin.disconnectSession();
  assert.equal(twin.session, 'disconnected');
  assert.equal(twin.type110.active, false);
  assert.equal(twin.type111.phase, 'idle');
  assert.deepEqual(twin.audio, {centerActive: false, voiceRouteActive: false, focusOwner: null});
  twin.startSession(stock);
  assert.equal(twin.type110.active, true, 'full disconnect did not permit clean reconnect');
  assert.equal(twin.type111.phase, 'idle');
  assert.deepEqual(twin.audio, {centerActive: false, voiceRouteActive: false, focusOwner: null});
}

{
  const twin = readyTwin();
  openSecondary(twin);
  twin.receiveFrame();
  twin.submitFrame();
  assert.ok(twin.events.some(event => event.type === 'type111_listener_started'));
  assert.ok(twin.events.some(event => event.type === 'type111_config_received'));
  assert.ok(twin.events.some(event => event.type === 'type111_frame_received'));
  assert.ok(twin.events.some(event => event.type === 'type110_still_active'));
  assert.deepEqual(twin.events.map(event => event.sequence),
    twin.events.map((_, index) => index), 'timeline sequence is not monotonic');
  twin.disconnectSession();
  assert.ok(twin.events.some(event => event.type === 'full_session_teardown'));
}

console.log('Type111 failure twin: negotiation, listener, crypto, parser, renderer, isolation, and teardown passed.');
