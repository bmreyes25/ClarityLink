/* Pure JS models: no Android, native library, USB, MFi, audio or bus execution. */
const ClarityServices = (() => {
  const twin = typeof module !== 'undefined' ? require('./digital-twin') : ClarityTwin;
  const ABI = Object.freeze({evidence: 'modeled ABI from receiver-multidisplay-audit.md; ARM not executed',
    callbackBytes: 24, pointerBits: 32, duplicateRegistrationResult: 0x16,
    offsets: Object.freeze({initialize: 0, finalize: 4, setProperty: 8, start: 12, stop: 16, processData: 20})});

  class MockBinder {
    constructor(services) { this.services = services; this.calls = []; }
    call(service, method, value) {
      if (!Object.hasOwn(this.services, service) || !Object.hasOwn(this.services[service], method))
        throw Error('Unmodeled Binder method');
      const result = this.services[service][method](value);
      this.calls.push({service, method}); // No private payload retained.
      return result;
    }
  }

  class ReceiverABIModel {
    constructor() {
      this.registered = false; this.phase = 'empty';
      this.usb = {attached: false, evidence: 'mocked transport'};
      this.mfi = {ready: false, evidence: 'mocked readiness; no MFi authentication'};
      this.display = {frame: null, properties: {}};
      this.audio = {focus: null, music: 'stopped', voice: 'idle', evidence: 'modeled continuity'};
    }
    register() {
      if (this.registered) return ABI.duplicateRegistrationResult;
      this.registered = true; return 0;
    }
    attach() { this.usb.attached = true; this.mfi.ready = true; }
    callback(name, value) {
      if (!Object.hasOwn(ABI.offsets, name)) throw Error('Unknown ABI callback');
      if (!this.registered) throw Error('Callback requires registration');
      if (name === 'initialize') {
        if (!this.usb.attached || !this.mfi.ready || this.phase !== 'empty') throw Error('Initialize requires mock transport');
        this.phase = 'ready';
      } else if (name === 'start') {
        if (this.phase !== 'ready') throw Error('Start requires initialization');
        this.phase = 'running';
      } else if (name === 'setProperty') {
        if (this.phase === 'empty') throw Error('Property requires initialization');
        if (!value || value.width !== 800 || value.height !== 480) throw Error('Modeled display is 800x480');
        this.display.properties = {width: 800, height: 480};
      } else if (name === 'processData') {
        if (this.phase !== 'running') throw Error('Data requires running receiver');
        if (typeof value !== 'string' || !/^[A-Za-z0-9_-]{1,64}$/.test(value)) throw Error('Expected symbolic frame ID');
        this.display.frame = value; // No proprietary packets, pixels or decoder.
      } else if (name === 'stop') {
        if (this.phase === 'empty') throw Error('Stop requires initialization');
        this.phase = 'ready'; this.display.frame = null;
      } else if (name === 'finalize') {
        this.phase = 'empty'; this.display = {frame: null, properties: {}};
      }
    }
    disconnect() {
      this.phase = 'empty'; this.registered = false;
      this.usb.attached = false; this.mfi.ready = false;
      this.display = {frame: null, properties: {}};
      this.audio = {...this.audio, focus: null, music: 'stopped', voice: 'idle'};
    }
  }

  class AndroidModel {
    constructor() {
      this.state = twin.blank(); this.receiver = new ReceiverABIModel();
      this.hondaGuidance = null; this.outputs = {center: null, hdmi: null};
      this.binder = new MockBinder({
        Navigation: {
          guidance: value => {
            if (!this.state.connected) throw Error('Guidance requires a session');
            if (!value || !['left', 'right', 'straight', 'arrive'].includes(value.maneuver) ||
                !Number.isFinite(value.distanceMeters) || value.distanceMeters < 0) throw Error('Invalid mock guidance');
            this.hondaGuidance = {...value, evidence: 'modeled Honda handler view; not CarPlay metadata',
                                  expiresAtMs: this.state.updatedMs + 15000};
          },
          end: () => { this.hondaGuidance = null; }
        },
        ExternalDisplay: {compose: () => {
          this.outputs.center = this.state.connected ? (this.state.centerCaptureId || this.state.centerApp) : null;
          this.outputs.hdmi = this.state.clusterStream.frameId ? 'synthetic:' + this.state.clusterStream.frameId :
            (this.state.clusterCaptureId ||
             (this.hondaGuidance ? 'modeled:honda-guidance' :
              this.state.display === 'casting' ? this.outputs.center : null));
        }},
        Audio: {update: value => {
          if (!this.state.connected) throw Error('Audio requires a session');
          if (!value || !['playing', 'paused', 'stopped'].includes(value.music) ||
              !['idle', 'speaking'].includes(value.voice)) throw Error('Invalid mock audio');
          this.receiver.audio = {...this.receiver.audio, focus: 'AvApService', music: value.music, voice: value.voice};
        }}
      });
    }
    apply(event) {
      const next = twin.apply(this.state, event); // Validate before changing services.
      this.state = next;
      if (event.type === 'connected') {
        this.receiver.disconnect(); this.hondaGuidance = null;
        this.receiver.attach(); this.receiver.register(); this.receiver.callback('initialize');
        this.receiver.callback('setProperty', {width: 800, height: 480}); this.receiver.callback('start');
      }
      if (event.type === 'disconnected') { this.receiver.disconnect(); this.hondaGuidance = null; }
      if (event.type === 'guidance-end') this.binder.call('Navigation', 'end');
      if (this.hondaGuidance && event.tMs >= this.hondaGuidance.expiresAtMs) this.hondaGuidance = null;
      this.binder.call('ExternalDisplay', 'compose');
      return this.state;
    }
  }
  function replayRuntimeSnapshots(catalog, serviceEvidence = null) {
    // Labels imply model actions; no captured ABI calls or transport bytes.
    const apps = {'02-carplay-home': 'home', '03-apple-maps-open': 'maps', '04-apple-maps-routing': 'maps',
      '05-route-center-music': 'music', '06-factory-cluster-navigation': 'music', '07-hondahack-casting': 'music'};
    const model = new AndroidModel(); const checkpoints = []; let tMs = 0;
    for (const snapshot of catalog.runtimeSnapshots) {
      const observed = serviceEvidence?.runtimeSnapshots.find(item => item.state === snapshot.state);
      if (serviceEvidence && (serviceEvidence.source !== catalog.source || !observed ||
          !Object.entries(snapshot.files).every(([name, reference]) => observed.sources[name]?.sha256 === reference.sha256)))
        throw Error('Runtime observation provenance mismatch');
      const disconnected = ['01-disconnected', '08-disconnected-again'].includes(snapshot.state);
      if (!disconnected && !Object.hasOwn(apps, snapshot.state)) throw Error('Unknown runtime state label');
      if (disconnected) model.apply({tMs: tMs++, type: 'disconnected'});
      else {
        if (!model.state.connected) model.apply({tMs: tMs++, type: 'connected'});
        model.apply({tMs: tMs++, type: 'center-app', app: apps[snapshot.state]});
      }
      checkpoints.push({state: snapshot.state, source: snapshot.source, files: snapshot.files,
        observed: observed ? 'hashed snapshot, acquisition label, allowlisted focus and bindings' : 'snapshot bytes/hashes and acquisition state label',
        inferred: 'connection/app from state label', synthetic: 'ABI calls and replay clock',
        unknown: 'USB/MFi payloads, protocol negotiation, per-event audio focus',
        receiverPhase: model.receiver.phase, centerApp: model.state.centerApp,
        audioFocus: model.receiver.audio.focus,
        observedAudioSnapshot: observed?.audio || null, observedBindings: observed?.activity.bindings || []});
    }
    return {model, checkpoints};
  }
  return {ABI, MockBinder, ReceiverABIModel, AndroidModel, replayRuntimeSnapshots};
})();
if (typeof module !== 'undefined') module.exports = ClarityServices;
