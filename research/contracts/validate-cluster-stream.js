#!/usr/bin/env node
/* Offline contract/lifecycle validator. No network, device, ADB, or vehicle I/O. */
const fs = require('node:fs');
const path = require('node:path');

const root = __dirname;
const schema = JSON.parse(fs.readFileSync(path.join(root, 'cluster-stream-v1.schema.json'), 'utf8'));
const VERSION = schema.$defs.base.properties.contractVersion.const;
const TYPES = new Set(schema.oneOf.map(x => x.$ref.split('/').pop()).map(name => schema.$defs[name].allOf[1].properties.type.const));
const ID = /^[A-Za-z0-9_-]{1,64}$/;
const FRAME_REF = /^bench:\/\/[A-Za-z0-9/_-]{1,160}$/;
const exactKeys = {
  'session-start': ['contractVersion','eventId','sessionId','atMs','type','audioPolicy','safetyScope'],
  'display-advertised': ['contractVersion','eventId','sessionId','atMs','type','display'],
  'stream-setup': ['contractVersion','eventId','sessionId','atMs','type','streamId','displayId','codec'],
  'stream-active': ['contractVersion','eventId','sessionId','atMs','type','streamId'],
  'frame-ready': ['contractVersion','eventId','sessionId','atMs','type','streamId','sequence','ptsUs','frameRef'],
  'stream-stop': ['contractVersion','eventId','sessionId','atMs','type','streamId','reason'],
  'session-stop': ['contractVersion','eventId','sessionId','atMs','type','reason'],
  'receiver-error': ['contractVersion','eventId','sessionId','atMs','type','scope','code','recoverable']
};
function fail(line, message) { throw Error(`line ${line}: ${message}`); }
function finiteInt(v, min, max=Number.MAX_SAFE_INTEGER) { return Number.isSafeInteger(v) && v >= min && v <= max; }
function enumValue(v, values) { return values.includes(v); }
function checkExactObject(o, keys, line, label) {
  if (!o || typeof o !== 'object' || Array.isArray(o)) fail(line, `${label} must be an object`);
  const got = Object.keys(o).sort(), wanted = [...keys].sort();
  if (got.join('\0') !== wanted.join('\0')) fail(line, `${label} fields differ: expected ${wanted.join(', ')}`);
}
function checkRect(r, line, label) {
  checkExactObject(r, ['x','y','width','height'], line, label);
  if (!finiteInt(r.x,0) || !finiteInt(r.y,0) || !finiteInt(r.width,1,4096) || !finiteInt(r.height,1,4096))
    fail(line, `${label} has invalid coordinates`);
}
function contains(outer, inner) {
  return inner.x >= outer.x && inner.y >= outer.y && inner.x + inner.width <= outer.x + outer.width && inner.y + inner.height <= outer.y + outer.height;
}
function checkDisplay(d, line) {
  checkExactObject(d, ['displayId','role','widthPixels','heightPixels','maxFps','viewArea','safeArea'], line, 'display');
  if (!ID.test(d.displayId) || !enumValue(d.role,['center','cluster-map','cluster-maneuver'])) fail(line,'invalid display identity/role');
  if (!finiteInt(d.widthPixels,1,4096) || !finiteInt(d.heightPixels,1,4096) || !finiteInt(d.maxFps,1,60)) fail(line,'invalid display dimensions/rate');
  checkRect(d.viewArea,line,'viewArea'); checkRect(d.safeArea,line,'safeArea');
  const physical={x:0,y:0,width:d.widthPixels,height:d.heightPixels};
  if (!contains(physical,d.viewArea) || !contains(d.viewArea,d.safeArea)) fail(line,'safe/view area exceeds its parent');
}
function validate(text) {
  const events=text.split(/\r?\n/).map(s=>s.trim()).filter(Boolean).map((s,i)=>{try{return JSON.parse(s)}catch{fail(i+1,'invalid JSON')}});
  const state={session:null,started:false,stopped:false,lastAt:-1,eventIds:new Set(),displays:new Map(),streams:new Map()};
  events.forEach((e,index)=>{
    const line=index+1;
    if (!e || typeof e!=='object' || Array.isArray(e) || !TYPES.has(e.type)) fail(line,'unknown event type');
    checkExactObject(e,exactKeys[e.type],line,'event');
    if (e.contractVersion!==VERSION || !ID.test(e.eventId) || !ID.test(e.sessionId) || !finiteInt(e.atMs,0)) fail(line,'invalid common fields');
    if (state.eventIds.has(e.eventId)) fail(line,'duplicate eventId'); state.eventIds.add(e.eventId);
    if (e.atMs<state.lastAt) fail(line,'time moved backwards'); state.lastAt=e.atMs;
    if (state.session && e.sessionId!==state.session) fail(line,'sessionId changed');
    if (state.stopped) fail(line,'event after session-stop');
    if (e.type==='session-start') {
      if (state.started || e.audioPolicy!=='preserve-existing-carplay' || e.safetyScope!=='navigation-region-only') fail(line,'invalid session start');
      state.started=true; state.session=e.sessionId; return;
    }
    if (!state.started) fail(line,'event before session-start');
    if (e.type==='display-advertised') {
      checkDisplay(e.display,line); if (state.displays.has(e.display.displayId)) fail(line,'display advertised twice');
      state.displays.set(e.display.displayId,e.display); return;
    }
    if (e.type==='stream-setup') {
      if (!ID.test(e.streamId) || !ID.test(e.displayId) || e.codec!=='h264' || !state.displays.has(e.displayId) || state.streams.has(e.streamId)) fail(line,'invalid stream setup');
      state.streams.set(e.streamId,{displayId:e.displayId,active:false,lastSequence:-1}); return;
    }
    if (e.type==='stream-active') {
      const s=state.streams.get(e.streamId); if (!s || s.active) fail(line,'stream cannot become active'); s.active=true; return;
    }
    if (e.type==='frame-ready') {
      const s=state.streams.get(e.streamId);
      if (!s?.active || !finiteInt(e.sequence,0) || e.sequence!==s.lastSequence+1 || !finiteInt(e.ptsUs,0) || !FRAME_REF.test(e.frameRef)) fail(line,'invalid frame/lifecycle');
      s.lastSequence=e.sequence; return;
    }
    if (e.type==='stream-stop') {
      const s=state.streams.get(e.streamId); if (!s?.active || !enumValue(e.reason,['route-ended','phone-request','disconnect','receiver-error','renderer-error'])) fail(line,'invalid stream stop');
      s.active=false; return;
    }
    if (e.type==='receiver-error') {
      if (!enumValue(e.scope,['session','center-stream','cluster-stream','renderer']) || !/^[A-Z0-9_]{1,64}$/.test(e.code) || typeof e.recoverable!=='boolean') fail(line,'invalid receiver error');
      return;
    }
    if (e.type==='session-stop') {
      if (![...state.streams.values()].every(s=>!s.active) || !enumValue(e.reason,['normal','disconnect','receiver-error'])) fail(line,'active stream at session stop or bad reason');
      state.stopped=true;
    }
  });
  if (!state.started || !state.stopped) throw Error('trace must contain session-start and session-stop');
  return {events:events.length,displays:state.displays.size,streams:state.streams.size,version:VERSION};
}
if (require.main===module) {
  const file=process.argv[2] || path.join(root,'cluster-stream-valid.jsonl');
  const result=validate(fs.readFileSync(file,'utf8'));
  console.log(`valid ${result.version}: ${result.events} events, ${result.displays} displays, ${result.streams} streams`);
}
module.exports={validate};
