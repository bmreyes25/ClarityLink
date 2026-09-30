// Synthetic-only lifecycle twin. It does not open sockets, derive real keys,
// decode proprietary payloads, call Android, or emulate Honda binaries.
'use strict';

const clone = value => JSON.parse(JSON.stringify(value));
const stable = value => JSON.stringify(value);

class Type111Failure extends Error {
  constructor(stage) {
    super('Synthetic Type111 failure at ' + stage);
    this.name = 'Type111Failure';
    this.stage = stage;
  }
}

class Type111FailureTwin {
  constructor() {
    this.session = 'disconnected';
    this.type110 = {active: false, response: null, cryptoCounter: 0, streamToken: null};
    this.type111 = this._emptyType111();
    this.audio = {centerActive: false, voiceRouteActive: false, focusOwner: null};
    this.events = [];
    this.nextGeneration = 1;
  }

  _emptyType111() {
    return {
      phase: 'idle', generation: null, response: null, streamConnectionID: null,
      dataPort: null, listener: 'closed', ctrCounter: 0, videoConfig: false,
      renderer: 'detached', frameCount: 0, unknownFields: ['Honda Type111 schema']
    };
  }

  _event(type, details = {}) {
    this.events.push({sequence: this.events.length, type, ...details});
  }

  startSession(stockType110Response) {
    if (this.session === 'connected') throw new Error('Session already connected');
    this.session = 'connected';
    this.type110 = {
      active: true,
      response: clone(stockType110Response),
      cryptoCounter: 0,
      streamToken: 'synthetic-type110'
    };
    this.type111 = this._emptyType111();
    this.audio = {centerActive: false, voiceRouteActive: false, focusOwner: null};
    this._event('session_started');
    this._event('type110_setup_preserved');
  }

  setAudio({centerActive, voiceRouteActive, focusOwner}) {
    if (this.session !== 'connected') throw new Error('Audio state requires session');
    this.audio = {centerActive: Boolean(centerActive), voiceRouteActive: Boolean(voiceRouteActive),
      focusOwner: focusOwner ?? null};
  }

  snapshotPrimary() {
    return stable({session: this.session, type110: this.type110, audio: this.audio});
  }

  _requireSession() {
    if (this.session !== 'connected') throw new Error('CarPlay session is not connected');
  }

  _fail(stage) {
    this._event('type111_listener_failed', {stage});
    this.type111 = this._emptyType111();
    if (this.type110.active) this._event('type110_still_active');
    return {ok: false, stage, stockResponse: clone(this.type110.response)};
  }

  requestType111({streamConnectionID, dataPort = 6100, failAt = null, unknownFields = []} = {}) {
    this._requireSession();
    this._event('type111_requested');
    if (failAt === 'unsupported-skipped') {
      this._event('type111_skipped_by_honda');
      this._event('type110_still_active');
      return {ok: false, stage: 'unsupported-skipped', stockResponse: clone(this.type110.response)};
    }
    if (!this.type110.active) return this._fail('type110-not-established');
    if (this.type111.phase !== 'idle') {
      this._event('type111_listener_failed', {stage: 'duplicate-request'});
      this._event('type110_still_active');
      return {ok: false, stage: 'duplicate-request', stockResponse: clone(this.type110.response)};
    }
    if (failAt === 'missing-display' || failAt === 'unknown-display-correlation')
      return this._fail(failAt);
    if (streamConnectionID === undefined || streamConnectionID === null)
      return this._fail('missing-stream-connection-id');
    if (!Number.isSafeInteger(streamConnectionID) || streamConnectionID <= 0)
      return this._fail('invalid-stream-connection-id');
    if (!Number.isInteger(dataPort) || dataPort < 1 || dataPort > 65535)
      return this._fail('invalid-data-port');
    if (failAt === 'missing-response-field' || failAt === 'malformed-request')
      return this._fail(failAt);
    this.type111 = {
      ...this._emptyType111(), phase: 'preparing', generation: this.nextGeneration++,
      streamConnectionID, dataPort, unknownFields: [...new Set([...unknownFields, 'Honda Type111 schema'])]
    };
    for (const stage of ['dataPort-allocation', 'bind', 'listen', 'crypto-derive', 'bad-iv', 'ctr-missing']) {
      if (failAt === stage) return this._fail(stage);
    }
    this.type111.listener = 'listening';
    this.type111.phase = 'advertised';
    this.type111.response = {type: 111, dataPort, streamConnectionID, evidence: 'synthetic-hypothesis'};
    this._event('type111_listener_started', {generation: this.type111.generation});
    this._event('type110_still_active');
    return {ok: true, response: clone(this.type111.response)};
  }

  connect({failAt = null} = {}) {
    this._requireSession();
    if (this.type111.phase !== 'advertised') return this._fail('not-advertised');
    if (failAt === 'accept-timeout' || failAt === 'teardown-while-accepting')
      return this._fail(failAt);
    this.type111.listener = 'connected';
    this.type111.phase = 'connected';
    this._event('type111_connected', {generation: this.type111.generation});
    return {ok: true};
  }

  receiveHeader({valid = true, failAt = null} = {}) {
    if (this.type111.phase !== 'connected') return this._fail('not-connected');
    if (failAt === 'disconnect-before-header' || failAt === 'disconnect-mid-header')
      return this._fail(failAt);
    if (!valid || failAt === 'malformed-128-byte-header') return this._fail('malformed-header');
    this.type111.phase = 'streaming';
    return {ok: true};
  }

  receiveConfig({valid = true, failAt = null} = {}) {
    if (this.type111.phase !== 'streaming') return this._fail('config-before-header');
    if (failAt === 'opcode1-before-key-ready' || failAt === 'decrypt-failure')
      return this._fail(failAt);
    if (!valid || failAt === 'missing-video-config' || failAt === 'malformed-video-config' ||
        failAt === 'unsupported-nal-length' || failAt === 'truncated-sps-pps')
      return this._fail(failAt || 'invalid-video-config');
    this.type111.ctrCounter += 1;
    this.type111.videoConfig = true;
    this._event('type111_config_received', {generation: this.type111.generation});
    return {ok: true};
  }

  receiveFrame({valid = true, failAt = null} = {}) {
    if (this.type111.phase !== 'streaming') return this._fail('frame-before-streaming');
    if (!this.type111.videoConfig || failAt === 'opcode0-before-config')
      return this._fail('frame-before-config');
    if (failAt === 'disconnect-mid-body' || failAt === 'body-too-large' ||
        failAt === 'truncated-avcc-nal' || failAt === 'h264-extractor-error' ||
        failAt === 'unknown-opcode' || failAt === 'decrypt-failure')
      return this._fail(failAt);
    if (!valid) return this._fail('invalid-frame');
    this.type111.ctrCounter += 1;
    this.type111.frameCount += 1;
    this._event('type111_frame_received', {generation: this.type111.generation});
    return {ok: true};
  }

  submitFrame({failAt = null} = {}) {
    if (this.type111.phase !== 'streaming' || this.type111.frameCount < 1)
      return this._fail('no-frame-to-render');
    if (['renderer-unavailable', 'renderer-bad-dimensions', 'renderer-timeout',
      'externaldisplay-host-unavailable', 'crop-mask-unknown', 'synthetic-frame-dropped']
      .includes(failAt)) {
      this._event('type111_renderer_failed', {stage: failAt});
      return this._fail(failAt);
    }
    this.type111.renderer = 'attached';
    return {ok: true};
  }

  disconnectType111(reason = 'type111-disconnect') {
    if (this.type111.phase !== 'idle') {
      this._event('type111_teardown', {reason, generation: this.type111.generation});
      this.type111 = this._emptyType111();
    }
    if (this.type110.active) this._event('type110_still_active');
  }

  disconnectType110() {
    this._requireSession();
    this.disconnectType111('parent-type110-disconnect');
    this.type110 = {active: false, response: null, cryptoCounter: 0, streamToken: null};
    this.session = 'connected';
    this._event('type110_disconnected');
  }

  disconnectSession() {
    if (this.session === 'connected') {
      this.disconnectType111('full-session-disconnect');
      this.type110 = {active: false, response: null, cryptoCounter: 0, streamToken: null};
      this.audio = {centerActive: false, voiceRouteActive: false, focusOwner: null};
      this.session = 'disconnected';
      this._event('full_session_teardown');
    }
  }
}

module.exports = {Type111Failure, Type111FailureTwin};
