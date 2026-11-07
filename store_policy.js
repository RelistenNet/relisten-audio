// Decides whether a cache miss should be written to the shared on-disk cache.
//
// Most plays are of files nobody requests again soon, and writing every miss
// saturated relisten2's disks. A file is stored once this pod has seen it
// requested by a second listener within the dictionary timeout (24h). Counts
// live in this pod's shared memory, so they reset on restart and each pod
// counts on its own; the stored files are shared by all pods.

// A web play requests a file more than once (the <audio> stream plus the Web
// Audio download), so each listener counts once per file.
function listenerKey(r) {
  // Cloudflare sets CF-Connecting-IP; audio-bare.relisten.net skips Cloudflare,
  // so fall back to the first X-Forwarded-For hop that Traefik adds.
  const forwardedFor = (r.headersIn['X-Forwarded-For'] || '').split(',')[0].trim();
  const client = r.headersIn['CF-Connecting-IP'] || forwardedFor || r.remoteAddress;

  return `listener:${client}:${r.uri}`;
}

function shouldStore(r) {
  // HEAD and other methods are not plays.
  if (r.method !== 'GET') {
    return '';
  }

  const dict = ngx.shared.store_policy;
  const countKey = `count:${r.uri}`;

  // add() succeeds only for a listener not yet counted for this file.
  const listeners = dict.add(listenerKey(r), 1) ? dict.incr(countKey, 1, 0) : dict.get(countKey);

  return listeners >= 2 ? '1' : '';
}

export default { shouldStore };
