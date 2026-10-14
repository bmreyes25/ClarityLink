# CL-IMP-08 H.264 fixtures

The red, blue, and green files are generated, clear H.264 Annex-B laboratory fixtures, not captured CarPlay content. Each contains two frames so delayed API17 decoder output can be drained; the 32×32 red/blue pair exercises independent stream contexts and the 64×64 green stream exercises decoder reset/resolution reconfiguration.

Reproduction command:

```sh
ffmpeg -hide_banner -loglevel error -f lavfi -i color=c=green:s=64x64:r=2 -frames:v 2 -c:v libx264 -preset ultrafast -tune zerolatency -profile:v baseline -x264-params keyint=30:scenecut=0 -f h264 pipe:1 | base64
```

Decoded fixture SHA-256 values:

- red 32×32: `171303000410d291b70cf61208be8ee6fab3361ff9a719a0df9005d5ece89410`
- blue 32×32: `c8c1b59060f01e41800153c097a7d3984f4b031214cbc7ccdf8e9d3bd56cf637`
- green 64×64: `67d1fe41ce2e1d39c9ef38aef66e3a49e074efd02159e19816805bc5bf5fbe21`
