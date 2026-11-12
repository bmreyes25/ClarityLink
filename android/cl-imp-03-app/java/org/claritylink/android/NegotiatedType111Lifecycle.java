package org.claritylink.android;

import java.util.concurrent.atomic.AtomicLong;

/**
 * API17 laboratory ownership adapter between the synthetic negotiation control plane and the
 * existing Binder receiver/presentation path. It owns identities and lifecycle fences only; frame
 * transport, decoding, and the Display 1 PaneLease remain owned by their existing components.
 */
final class NegotiatedType111Lifecycle {
    private static final AtomicLong NEXT_MODEL_GENERATION = new AtomicLong(1L);

    static final class Snapshot {
        final String state;
        final long parentGeneration;
        final long childGeneration;
        final long streamGeneration;
        final long decoderGeneration;
        final long producerGeneration;
        final long presentationGeneration;
        final int receiverPid;
        final int producerPid;
        final boolean candidateEnabled;
        final boolean presentationSelected;
        final long deliveredFrames;

        Snapshot(NegotiatedType111Lifecycle owner) {
            state = owner.state;
            parentGeneration = owner.parentGeneration;
            childGeneration = owner.childGeneration;
            streamGeneration = owner.child == null ? 0L : owner.child.streamGeneration;
            decoderGeneration = owner.decoderGeneration;
            producerGeneration = owner.producerGeneration;
            presentationGeneration = owner.presentationGeneration;
            receiverPid = owner.receiverPid;
            producerPid = owner.producerPid;
            candidateEnabled = owner.candidateEnabled;
            presentationSelected = owner.presentationSelected;
            deliveredFrames = owner.deliveredFrames;
        }
    }

    private final FrameStreamIdentity parentOwner;
    private final long parentGeneration;
    private String state = "PARENT_ACTIVE";
    private boolean candidateEnabled;
    private FrameStreamIdentity pending;
    private FrameStreamIdentity child;
    private long childGeneration;
    private long decoderGeneration;
    private long producerGeneration;
    private long presentationGeneration;
    private int receiverPid;
    private int producerPid;
    private boolean presentationSelected;
    private long deliveredFrames;

    NegotiatedType111Lifecycle(FrameStreamIdentity parentOwner) {
        if (parentOwner == null || !parentOwner.isValid() ||
                parentOwner.streamType != FrameStreamIdentity.TYPE110)
            throw new IllegalArgumentException("type110_parent_owner_required");
        this.parentOwner = parentOwner;
        this.parentGeneration = nextGeneration(NEXT_MODEL_GENERATION);
    }

    synchronized String enableCandidate() {
        if (!"PARENT_ACTIVE".equals(state) || candidateEnabled) return "candidate_enable_rejected";
        candidateEnabled = true;
        state = "CANDIDATE_ENABLED";
        return "accepted";
    }

    synchronized String setup(FrameStreamIdentity identity) {
        if (!candidateEnabled || child != null || pending != null ||
                !isChildOfParent(identity)) return "type111_setup_rejected";
        pending = identity;
        state = "SETUP_PENDING";
        return "accepted";
    }

    synchronized String activate(FrameStreamIdentity identity, int actualReceiverPid) {
        if (!candidateEnabled || pending == null || !pending.equals(identity) ||
                actualReceiverPid <= 0) return "type111_receiver_not_ready";
        child = identity;
        pending = null;
        childGeneration = nextGeneration(NEXT_MODEL_GENERATION);
        producerGeneration = 0L;
        receiverPid = actualReceiverPid;
        producerPid = 0;
        decoderGeneration = 0L;
        presentationSelected = false;
        deliveredFrames = 0L;
        state = "TYPE111_RECEIVER_ACTIVE";
        return "accepted";
    }

    synchronized String producerBound(FrameStreamIdentity identity, int actualProducerPid) {
        if (!matchesChild(identity) || actualProducerPid <= 0 || receiverPid <= 0)
            return "type111_producer_rejected";
        if (producerPid == actualProducerPid) return "accepted";
        if (producerGeneration == Long.MAX_VALUE) throw new IllegalStateException("generation_exhausted");
        producerGeneration++;
        producerPid = actualProducerPid;
        return "accepted";
    }

    synchronized String producerDied(FrameStreamIdentity identity, int deadProducerPid) {
        if (!matchesChild(identity) || deadProducerPid <= 0 || producerPid != deadProducerPid)
            return "stale_type111_producer_death";
        clearChild();
        state = candidateEnabled ? "CANDIDATE_ENABLED" : "PARENT_ACTIVE";
        return "accepted";
    }

    synchronized String decoderReady(FrameStreamIdentity identity, long newDecoderGeneration,
            int width, int height) {
        if (!matchesChild(identity) || receiverPid <= 0 || newDecoderGeneration <= 0 ||
                width <= 0 || height <= 0 || width > 1920 || height > 1080)
            return "type111_decoder_rejected";
        if (decoderGeneration != 0L && newDecoderGeneration <= decoderGeneration)
            return "stale_type111_decoder_generation";
        decoderGeneration = newDecoderGeneration;
        if (!"NAVIGATION_PRESENTATION_ACTIVE".equals(state)) state = "TYPE111_DECODER_READY";
        return "accepted";
    }

    synchronized String transportGeneration(FrameStreamIdentity oldIdentity,
            FrameStreamIdentity newIdentity, int actualReceiverPid) {
        if (!matchesChild(oldIdentity) || newIdentity == null || !newIdentity.isValid() ||
                actualReceiverPid <= 0 ||
                newIdentity.streamType != FrameStreamIdentity.TYPE111 ||
                newIdentity.sessionId != parentOwner.sessionId ||
                newIdentity.connectionId != oldIdentity.connectionId ||
                newIdentity.outputId != oldIdentity.outputId ||
                newIdentity.streamGeneration <= oldIdentity.streamGeneration)
            return "invalid_type111_transport_generation";
        child = newIdentity;
        receiverPid = actualReceiverPid;
        producerPid = 0;
        producerGeneration = 0L;
        decoderGeneration = 0L;
        presentationGeneration++;
        presentationSelected = false;
        deliveredFrames = 0L;
        childGeneration = nextGeneration(NEXT_MODEL_GENERATION);
        state = "TYPE111_RECEIVER_ACTIVE";
        return "accepted";
    }

    synchronized String presentation(FrameStreamIdentity identity, boolean selected) {
        if (!matchesChild(identity)) return "stale_or_inactive_type111";
        if (presentationSelected != selected) presentationGeneration++;
        presentationSelected = selected;
        if (selected) state = "NAVIGATION_PRESENTATION_ACTIVE";
        else if (decoderGeneration > 0L) state = "TYPE111_DECODER_READY";
        else state = "TYPE111_RECEIVER_ACTIVE";
        return "accepted";
    }

    /** Records a successful downstream Binder response after the existing host lease accepted a frame. */
    synchronized String frameDelivered(FrameStreamIdentity identity, long frameId) {
        if (!matchesChild(identity) || !presentationSelected || decoderGeneration <= 0L || frameId <= 0L)
            return "type111_frame_not_presentable";
        deliveredFrames++;
        return "accepted";
    }

    synchronized String withdrawChild(FrameStreamIdentity identity) {
        if (child == null || identity == null || !child.equals(identity)) {
            if (child == null && pending == null) return "already_withdrawn";
            return "stale_type111_teardown";
        }
        clearChild();
        state = candidateEnabled ? "CANDIDATE_ENABLED" : "PARENT_ACTIVE";
        return "accepted";
    }

    synchronized void parentTeardown() {
        if ("PARENT_CLOSED".equals(state)) return;
        pending = null;
        clearChild();
        candidateEnabled = false;
        state = "PARENT_CLOSED";
    }

    synchronized Snapshot snapshot() { return new Snapshot(this); }

    synchronized boolean parentIsActive() { return !"PARENT_CLOSED".equals(state); }

    private boolean matchesChild(FrameStreamIdentity identity) {
        return child != null && child.equals(identity) && parentIsActive();
    }

    private boolean isChildOfParent(FrameStreamIdentity identity) {
        return identity != null && identity.isValid() &&
                identity.streamType == FrameStreamIdentity.TYPE111 &&
                identity.sessionId == parentOwner.sessionId &&
                identity.connectionId != parentOwner.connectionId;
    }

    private void clearChild() {
        pending = null;
        child = null;
        decoderGeneration = 0L;
        producerGeneration = 0L;
        receiverPid = 0;
        producerPid = 0;
        presentationSelected = false;
        deliveredFrames = 0L;
    }

    private static long nextGeneration(AtomicLong source) {
        long value = source.getAndIncrement();
        if (value <= 0L || value == Long.MAX_VALUE) throw new IllegalStateException("generation_exhausted");
        return value;
    }
}
