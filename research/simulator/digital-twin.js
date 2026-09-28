/* Offline event replay. No network, ADB, Binder, CAN, or device output. */
const ClarityTwin = (() => {
  const captures = Object.freeze({
    'center-maps': 'center', 'center-music': 'center',
    'cluster-maps': 'cluster', 'cluster-navigation': 'cluster',
    'center-20260925-native-maps': 'center', 'cluster-20260925-native': 'cluster',
    'center-20260925-cast-maps': 'center', 'cluster-20260925-cast-maps': 'cluster',
    'center-20260925-music': 'center', 'cluster-20260925-cast-music': 'cluster',
    'center-20260925-waze-route': 'center', 'cluster-20260925-waze-route': 'cluster',
    'center-20260925-honda-home': 'center', 'center-20260925-waze-ended': 'center',
    'cluster-20260925-waze-ended': 'cluster'
  });
  const blankClusterStream = () => ({advertised: false, setup: false, active: false, frameId: null, frames: 0, expiresAtMs: null});
  const blank = () => ({
    source: 'synthetic', connected: false, navigation: null,
    speedKph: 0, gear: 'P', batterySocPercent: 70, evRangeKm: 70,
    display: 'native', voiceGuidance: 'unobserved', centerApp: 'none',
    clusterStream: blankClusterStream(), centerCaptureId: null, clusterCaptureId: null, updatedMs: 0
  });
  function apply(state, event) {
    if (!event || typeof event !== 'object' || !Number.isFinite(event.tMs) || event.tMs < state.updatedMs)
      throw Error('Invalid or out-of-order event time');
    const next = {...state, updatedMs: event.tMs};
    if (next.navigation && event.tMs >= next.navigation.expiresAtMs) next.navigation = null;
    if (next.clusterStream.expiresAtMs !== null && event.tMs >= next.clusterStream.expiresAtMs)
      next.clusterStream = blankClusterStream();
    if (event.type === 'connected') return {...blank(), connected: true, updatedMs: event.tMs};
    else if (event.type === 'disconnected') {
      next.connected = false; next.navigation = null; next.display = 'native';
      next.centerApp = 'none'; next.clusterStream = blankClusterStream();
      next.centerCaptureId = null; next.clusterCaptureId = null;
    }
    else if (event.type === 'guidance') {
      if (!next.connected) throw Error('Guidance requires a connected session');
      if (!['left', 'right', 'straight', 'roundabout', 'arrive', 'unknown'].includes(event.maneuver))
        throw Error('Unknown maneuver');
      if (!Number.isFinite(event.distanceMeters) || event.distanceMeters < 0 || event.distanceMeters > 100000)
        throw Error('Invalid distance');
      if (typeof event.road !== 'string' || event.road.length > 100) throw Error('Invalid road');
      const sourceKind = event.sourceKind || 'synthetic';
      if (!['synthetic', 'center-ocr', 'route-metadata'].includes(sourceKind)) throw Error('Invalid guidance source');
      next.navigation = {maneuver: event.maneuver, road: event.road, distanceMeters: event.distanceMeters,
                         provenance: event.provenance || 'synthetic', sourceKind,
                         expiresAtMs: event.tMs + 15000, tMs: event.tMs};
    }
    else if (event.type === 'guidance-end') {
      next.navigation = null;
      next.clusterStream = blankClusterStream();
    }
    else if (event.type === 'center-app') {
      if (!next.connected) throw Error('Center app requires a connected session');
      if (!['maps', 'music', 'waze', 'home', 'other'].includes(event.app)) throw Error('Invalid center app');
      next.centerApp = event.app;
      if (event.app !== 'maps' && next.navigation?.sourceKind === 'center-ocr') next.navigation = null;
    }
    else if (event.type === 'capture-frame') {
      if (!next.connected) throw Error('Captured frame requires a connected session');
      if (!['center', 'cluster'].includes(event.display)) throw Error('Invalid capture display');
      if (captures[event.captureId] !== event.display) throw Error('Invalid capture ID for display');
      if (event.display === 'center') next.centerCaptureId = event.captureId;
      else next.clusterCaptureId = event.captureId;
    }
    else if (event.type === 'receiver-capabilities') {
      if (!next.connected || next.clusterStream.setup) throw Error('Capabilities require a connected session before setup');
      if (typeof event.clusterDisplay !== 'boolean') throw Error('Invalid cluster capability');
      next.clusterStream = {...blankClusterStream(), advertised: event.clusterDisplay};
    }
    else if (event.type === 'cluster-setup') {
      if (!next.connected || !next.clusterStream.advertised || next.clusterStream.setup)
        throw Error('Cluster setup requires an advertised, unused display');
      next.clusterStream = {...next.clusterStream, setup: true};
    }
    else if (event.type === 'cluster-activate') {
      if (!next.connected || !next.clusterStream.setup) throw Error('Cluster activation requires setup');
      next.clusterStream = {...next.clusterStream, active: true};
    }
    else if (event.type === 'cluster-frame') {
      if (!next.connected || !next.clusterStream.active) throw Error('Cluster frame requires an active stream');
      if (typeof event.frameId !== 'string' || !/^[a-zA-Z0-9_-]{1,64}$/.test(event.frameId))
        throw Error('Invalid frame ID');
      next.clusterStream = {...next.clusterStream, frameId: event.frameId, frames: next.clusterStream.frames + 1,
                            expiresAtMs: event.tMs + 15000};
    }
    else if (event.type === 'cluster-stop') next.clusterStream = blankClusterStream();
    else if (event.type === 'display') {
      if (!['native', 'casting', 'guidance-card'].includes(event.mode)) throw Error('Invalid display');
      next.display = event.mode;
    }
    else if (event.type === 'voice') {
      if (!['heard', 'silent', 'unobserved'].includes(event.status)) throw Error('Invalid voice status');
      next.voiceGuidance = event.status;
    }
    else if (event.type === 'vehicle') {
      for (const [name, min, max] of [['speedKph', 0, 250], ['batterySocPercent', 0, 100], ['evRangeKm', 0, 1000]]) {
        if (event[name] !== undefined) {
          if (!Number.isFinite(event[name]) || event[name] < min || event[name] > max) throw Error('Invalid ' + name);
          next[name] = event[name];
        }
      }
      if (event.gear !== undefined) {
        if (!['P', 'R', 'N', 'D', 'B'].includes(event.gear)) throw Error('Invalid gear');
        next.gear = event.gear;
      }
    }
    else if (event.type !== 'tick') throw Error('Unknown event type');
    return next;
  }
  function replay(events) {return events.reduce(apply, blank());}
  function parseJSONL(text) {
    return text.split(/\r?\n/).map(s => s.trim()).filter(Boolean).map((s, i) => {
      try {return JSON.parse(s);} catch {throw Error('Invalid JSON on line ' + (i + 1));}
    });
  }
  return {blank, apply, replay, parseJSONL, captures};
})();
if (typeof module !== 'undefined') module.exports = ClarityTwin;
