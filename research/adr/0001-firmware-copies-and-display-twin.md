# ADR-0001: Use working firmware copies and captured display replay

**Date:** 2026-09-24  
**Status:** Accepted  
**Deciders:** ClarityLab owner and Codex

## Context

The user wants fast experimentation with a cluster guidance display. The verified original backup is the only recovery reference. The current Honda receiver advertises one main CarPlay screen, while saved captures show an Android HDMI cluster output. The existing simulator showed abstract states but not the observed displays.

## Decision

Keep the verified original backup immutable. Place editable copies of the relevant firmware layout and CarPlay display configuration inside the simulator workspace, derive dimensions from them, and replay the captured center and HDMI frames. Show proposed guidance separately from captured pixels until its physical placement and on-car behavior are measured.

## Alternatives considered

### Modify the original backup

This would put the recovery baseline at risk and make later diffs unreliable. Rejected.

### Patch receiver binaries immediately

The display negotiation, per-stream proxy dispatch, decoder capacity, and recovery method are not established. Rejected for this stage.

### Keep only a schematic simulator

It cannot expose differences between the observed center and HDMI outputs or verify frame cleanup. Rejected as the sole test surface.

## Consequences

The simulator now makes source versus proposed behavior visible and reproducible without powering the car. It cannot prove physical cluster placement, iPhone negotiation, sustained video decode, or voice behavior after a future change. Any receiver experiment must start from a diff against the immutable baseline and pass a separate recovery review.
