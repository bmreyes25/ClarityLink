const fs = require('node:fs');
const path = require('node:path');
const {validate} = require('../contracts/validate-cluster-stream');
const {adapt} = require('./contract-adapter');

const source = fs.readFileSync(path.join(__dirname, '../contracts/cluster-stream-center-music.jsonl'), 'utf8');
validate(source);
const contract = source.trim().split('\n').map(JSON.parse);
const mapped = adapt(contract);
mapped.splice(1, 0, {tMs: 0, type: 'center-app', app: 'maps'});
const secondFrame = mapped.findIndex(e => e.type === 'cluster-frame' && e.frameId === 'cluster-0001');
if (secondFrame < 0) throw Error('Expected second cluster frame');
mapped.splice(secondFrame, 0, {tMs: 6, type: 'center-app', app: 'music'});
const output = mapped.map(e => JSON.stringify(e)).join('\n') + '\n';
fs.writeFileSync(path.join(__dirname, 'sample-contract-replay.jsonl'), output);
