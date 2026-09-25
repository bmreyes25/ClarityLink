/* Offline adapter from validated bench contract events to the browser twin. */
function adapt(events) {
  const output = [];
  const displays = new Map();
  const streams = new Map();
  let clusterAdvertised = false;
  for (const event of events) {
    const tMs = event.atMs;
    if (event.type === 'session-start') output.push({tMs, type: 'connected'});
    else if (event.type === 'display-advertised') {
      displays.set(event.display.displayId, event.display.role);
      if (event.display.role.startsWith('cluster-')) {
        if (clusterAdvertised) throw Error('Twin supports one cluster stream at a time');
        clusterAdvertised = true;
        output.push({tMs, type: 'receiver-capabilities', clusterDisplay: true});
      }
    }
    else if (event.type === 'stream-setup') {
      const role = displays.get(event.displayId);
      if (!role) throw Error('Stream references an unknown display');
      streams.set(event.streamId, role);
      if (role.startsWith('cluster-')) output.push({tMs, type: 'cluster-setup'});
    }
    else if (event.type === 'stream-active') {
      if (streams.get(event.streamId)?.startsWith('cluster-')) output.push({tMs, type: 'cluster-activate'});
    }
    else if (event.type === 'frame-ready') {
      if (!/^bench:\/\/[A-Za-z0-9/_-]{1,160}$/.test(event.frameRef)) throw Error('Invalid bench frame reference');
      if (streams.get(event.streamId)?.startsWith('cluster-')) {
        const frameId = event.frameRef.split('/').pop();
        if (!/^[A-Za-z0-9_-]{1,64}$/.test(frameId)) throw Error('Invalid bench frame ID');
        output.push({tMs, type: 'cluster-frame', frameId});
      }
    }
    else if (event.type === 'stream-stop') {
      if (streams.get(event.streamId)?.startsWith('cluster-')) {
        if (event.reason === 'route-ended') output.push({tMs, type: 'guidance-end'});
        output.push({tMs, type: 'cluster-stop'});
      }
    }
    else if (event.type === 'receiver-error') {
      if (['cluster-stream','renderer'].includes(event.scope)) output.push({tMs, type: 'cluster-stop'});
      if (event.scope === 'session') output.push({tMs, type: 'disconnected'});
    }
    else if (event.type === 'session-stop') output.push({tMs, type: 'disconnected'});
    else throw Error('Unknown contract event');
  }
  return output;
}
module.exports = {adapt};
