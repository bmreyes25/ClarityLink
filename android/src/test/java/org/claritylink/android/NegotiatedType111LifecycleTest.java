package org.claritylink.android;

import java.util.HashSet;

/** Host-executable contract test for the API17-compatible negotiated-media lifecycle adapter. */
public final class NegotiatedType111LifecycleTest {
    private static int assertions;

    public static void main(String[] args) {
        adapterContracts();
        controlPlaneIntegration();
        System.out.println("NEGOTIATED_TYPE111_LIFECYCLE_PASS assertions=" + assertions +
                " default=disabled parent_preserved=true child_cleanup=verified");
    }

    private static void adapterContracts() {
        FrameStreamIdentity parent = type110(100L, 11001L, 4L);
        NegotiatedType111Lifecycle lifecycle = new NegotiatedType111Lifecycle(parent);
        check(!lifecycle.snapshot().candidateEnabled, "candidate starts disabled");
        check("type111_setup_rejected".equals(lifecycle.setup(type111(100L, 11101L, 1L))),
                "setup blocked before candidate opt-in");
        check("accepted".equals(lifecycle.enableCandidate()), "explicit candidate opt-in");
        check("candidate_enable_rejected".equals(lifecycle.enableCandidate()), "duplicate opt-in rejected");
        check("type111_setup_rejected".equals(lifecycle.setup(type111(100L, 11001L, 1L))),
                "child cannot reuse Type110 connection");

        FrameStreamIdentity child = type111(100L, 11101L, 1L);
        check("type111_setup_rejected".equals(lifecycle.setup(type111(101L, 11101L, 1L))),
                "wrong parent session rejected");
        check("accepted".equals(lifecycle.setup(child)), "valid child setup accepted");
        check("type111_setup_rejected".equals(lifecycle.setup(child)), "duplicate child setup rejected");
        check("type111_receiver_not_ready".equals(lifecycle.activate(child, 0)),
                "missing receiver owner rejected");
        check("accepted".equals(lifecycle.activate(child, 3001)), "bound receiver activates child");

        NegotiatedType111Lifecycle.Snapshot active = lifecycle.snapshot();
        check(active.parentGeneration > 0L && active.childGeneration > 0L,
                "model generations allocated");
        check(active.parentGeneration != active.childGeneration,
                "parent and child generations remain distinct");
        check(active.streamGeneration == child.streamGeneration && active.receiverPid == 3001,
                "stream identity and receiver owner retained separately");
        check("type111_producer_rejected".equals(lifecycle.producerBound(child, 0)),
                "invalid producer rejected");
        check("accepted".equals(lifecycle.producerBound(child, 3002)),
                "producer admission tentatively binds its identity");
        check("accepted".equals(lifecycle.producerBindFailed(child, 3002)),
                "failed authorization rolls back the tentative producer identity");
        check(lifecycle.snapshot().producerPid == 0 &&
                "type111_frame_not_presentable".equals(lifecycle.frameDelivered(child, 1L)),
                "failed producer admission leaves no media authority");
        check("accepted".equals(lifecycle.producerBound(child, 3002)),
                "producer binds after a successful authorization retry");
        check("type111_decoder_rejected".equals(lifecycle.decoderReady(
                child.withGeneration(2L), 1L, 32, 32)), "wrong stream generation rejected");
        check("type111_decoder_rejected".equals(lifecycle.decoderReady(child, 0L, 32, 32)),
                "missing decoder generation rejected");
        check("accepted".equals(lifecycle.decoderReady(child, 9L, 32, 32)),
                "decoder generation accepted");
        check("stale_type111_decoder_generation".equals(lifecycle.decoderReady(child, 8L, 32, 32)),
                "stale decoder generation rejected");
        check("type111_frame_not_presentable".equals(lifecycle.frameDelivered(child, 1L)),
                "frame blocked before presentation selection");
        check("accepted".equals(lifecycle.presentation(child, true)), "presentation selected");
        check("type111_frame_not_presentable".equals(lifecycle.frameDelivered(child, 0L)),
                "invalid frame id rejected");
        check("accepted".equals(lifecycle.frameDelivered(child, 12L)),
                "host-accepted frame recorded");
        check(lifecycle.snapshot().deliveredFrames == 1L, "frame receipt counted");

        check("accepted".equals(lifecycle.producerBound(child, 3002)),
                "duplicate binding by current producer is idempotent");
        check("accepted".equals(lifecycle.producerBound(child, 3003)),
                "authorized restarted producer receives a new producer epoch");
        check(lifecycle.snapshot().producerGeneration == 3L,
                "producer generation remains independent from child and stream generations");
        check("stale_type111_producer_death".equals(lifecycle.producerDied(child, 3002)),
                "wrong producer death callback rejected");
        check("accepted".equals(lifecycle.producerDied(child, 3003)),
                "actual producer death revokes its child media ownership");
        check("type111_frame_not_presentable".equals(lifecycle.frameDelivered(child, 13L)),
                "dead child cannot present a late frame");
        check(lifecycle.parentIsActive() && lifecycle.snapshot().state.equals("TYPE111_PRODUCER_RESTART_REQUIRED"),
                "producer failure preserves parent and fences child media until a new producer binds");
        check("accepted".equals(lifecycle.producerBound(child, 3004)),
                "authorized replacement producer binds to the live child");
        check(lifecycle.snapshot().producerGeneration == 4L,
                "replacement producer receives a new independent generation");
        check("stale_type111_producer_death".equals(lifecycle.producerDied(child, 3003)),
                "late old producer death cannot revoke its replacement");
        check("accepted".equals(lifecycle.decoderReady(child, 1L, 32, 32)),
                "replacement producer initializes a fresh decoder generation");
        check("type111_frame_not_presentable".equals(lifecycle.frameDelivered(child, 14L)),
                "presentation remains hidden after producer death");
        check("accepted".equals(lifecycle.presentation(child, true)), "replacement presentation selected");
        check("accepted".equals(lifecycle.frameDelivered(child, 15L)),
                "replacement producer can deliver a new frame");
        check("accepted".equals(lifecycle.withdrawChild(child)), "current child withdrawn");
        check("already_withdrawn".equals(lifecycle.withdrawChild(child)),
                "repeated child teardown is idempotent");
        check(lifecycle.parentIsActive(), "child withdrawal preserves parent");
        lifecycle.parentTeardown();
        lifecycle.parentTeardown();
        check(!lifecycle.parentIsActive(), "parent teardown is idempotent");
        check("candidate_enable_rejected".equals(lifecycle.enableCandidate()),
                "closed parent cannot reopen candidate");
        check(parent.equals(type110(100L, 11001L, 4L)), "Type110 identity is unchanged");
    }

    private static void controlPlaneIntegration() {
        FrameStreamIdentity parent = type110(200L, 22001L, 7L);
        FrameStreamIdentity child = type111(200L, 22111L, 1L);
        Type111ControlPlane plane = new Type111ControlPlane(parent);
        HashSet<String> contexts = new HashSet<String>();
        contexts.add(Type111ControlPlane.MAP_CONTEXT);
        check("accepted".equals(plane.registerCapability(new Type111ControlPlane.Capability(
                200L, "api17-lab-secondary", 800, 480, 30, contexts))),
                "control-plane capability opens adapter");
        check("accepted".equals(plane.setup(child)), "control-plane setup enters adapter");
        check("accepted".equals(plane.activate(child, 4001)), "control-plane receiver binds");
        check("accepted".equals(plane.producerBound(child, 4003)),
                "control-plane starts a tentative producer bind");
        check("accepted".equals(plane.producerBindFailed(child, 4003)),
                "control-plane rolls a failed producer bind back");
        check(plane.snapshot().producerPid == 0 &&
                "type111_frame_not_presentable".equals(plane.frameDelivered(child, 4L)),
                "failed producer authorization leaves the media path closed");
        check("accepted".equals(plane.producerBound(child, 4002)), "control-plane producer binds");
        check("accepted".equals(plane.videoConfig(child, 32, 32)), "control-plane decoder binds");
        check("accepted".equals(plane.navigation(child, "maps", true, false)),
                "control-plane navigation becomes eligible");
        check("accepted".equals(plane.presentation(child, "suggestUI", Type111ControlPlane.MAP_CONTEXT)),
                "control-plane accepts navigation context");
        check("accepted".equals(plane.presentation(child, "showUI", null)),
                "control-plane selection updates adapter");
        check("accepted".equals(plane.frameDelivered(child, 5L)),
                "adapter records downstream accepted frame");
        check("accepted".equals(plane.producerDied(child, 4002)),
                "control plane consumes actual producer death");
        check(plane.snapshot().state.equals("TYPE111_STREAM_ACTIVE") &&
                plane.snapshot().modelChildGeneration > 0L && plane.snapshot().producerPid == 0,
                "producer death clears media ownership but preserves receiver child identity");
        check("type111_frame_not_presentable".equals(plane.frameDelivered(child, 6L)),
                "frame delivery is fenced until producer restart");
        check("accepted".equals(plane.producerBound(child, 4002)),
                "replacement producer rebinds after death");
        check("accepted".equals(plane.videoConfig(child, 32, 32)),
                "replacement producer installs fresh decoder generation");
        check("accepted".equals(plane.presentation(child, "suggestUI", Type111ControlPlane.MAP_CONTEXT)),
                "replacement producer requests navigation presentation again");
        check("accepted".equals(plane.presentation(child, "showUI", null)),
                "replacement producer restores a fresh presentation selection");
        check("accepted".equals(plane.frameDelivered(child, 7L)),
                "replacement producer delivers after new presentation is selected");
        Type111ControlPlane.Snapshot active = plane.snapshot();
        check(active.candidateEnabled && active.modelParentGeneration != active.modelChildGeneration,
                "control-plane exposes separate model generations");
        check(active.deliveredFrames == 1L && active.modelPresentationGeneration > 0L,
                "presentation receipt and generation retained");
        check("accepted".equals(plane.teardown(child)), "child teardown succeeds");
        check(plane.snapshot().state.equals("SECONDARY_CAPABILITY_REGISTERED"),
                "child teardown leaves parent capability active");
        plane.parentTeardown();
        check(plane.snapshot().state.equals("TEARDOWN"), "parent teardown closes control plane");
    }

    private static FrameStreamIdentity type110(long session, long connection, long generation) {
        return new FrameStreamIdentity(session, FrameStreamIdentity.TYPE110, connection, generation,
                FrameStreamIdentity.OUTPUT_PRIMARY_LAB);
    }

    private static FrameStreamIdentity type111(long session, long connection, long generation) {
        return new FrameStreamIdentity(session, FrameStreamIdentity.TYPE111, connection, generation,
                FrameStreamIdentity.OUTPUT_SECONDARY_VIEW);
    }

    private static void check(boolean condition, String label) {
        assertions++;
        if (!condition) throw new AssertionError(label);
    }
}
