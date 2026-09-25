const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {validate}=require('./validate-cluster-stream');
const valid=fs.readFileSync(path.join(__dirname,'cluster-stream-valid.jsonl'),'utf8');
assert.equal(validate(valid).events,8);
const rows=valid.trim().split('\n').map(JSON.parse);
function rejected(change, pattern) {
  const copy=structuredClone(rows); change(copy);
  assert.throws(()=>validate(copy.map(JSON.stringify).join('\n')),pattern);
}
rejected(x=>{x[2].display.safeArea.width=750},/safe\/view area/);
rejected(x=>{x[4].streamId='missing'},/stream cannot become active/);
rejected(x=>{x[5].sequence=2},/invalid frame/);
rejected(x=>{x[5].frameRef='file:///private/frame'},/invalid frame/);
rejected(x=>{x[6].reason='unknown'},/invalid stream stop/);
rejected(x=>{x[4].extra=true},/fields differ/);
rejected(x=>{x.splice(6,1)},/active stream at session stop/);
console.log('Cluster-stream v1 contract: valid lifecycle and seven rejection paths passed.');
