package org.claritylink.android;

import java.util.HashSet;
import java.util.Set;

/** Synthetic, API17-compatible Type111 lifecycle model for the isolated lab receiver. */
final class Type111ControlPlane {
    static final String MAP_CONTEXT = "maps:/car/instrumentcluster/map";
    static final String INSTRUCTION_CONTEXT = "maps:/car/instrumentcluster/instructioncard";

    static final class Capability {
        final long sessionId;
        final String displayUuid;
        final int width;
        final int height;
        final int maxFramesPerSecond;
        final Set<String> contexts;

        Capability(long sessionId, String displayUuid, int width, int height, int maxFramesPerSecond,
                Set<String> contexts) {
            if (sessionId <= 0 || displayUuid == null || displayUuid.length() == 0 ||
                    displayUuid.length() > 64 || width <= 0 || width > 1920 ||
                    height <= 0 || height > 1080 || maxFramesPerSecond <= 0 ||
                    maxFramesPerSecond > 60 || contexts == null || contexts.size() == 0 ||
                    contexts.size() > 2 || !contexts.contains(MAP_CONTEXT) ||
                    !validContexts(contexts)) throw new IllegalArgumentException("invalid_type111_capability");
            this.sessionId = sessionId;
            this.displayUuid = displayUuid;
            this.width = width;
            this.height = height;
            this.maxFramesPerSecond = maxFramesPerSecond;
            this.contexts = new HashSet<String>(contexts);
        }
    }

    static final class Snapshot {
        final String state;
        final long sessionId;
        final long connectionId;
        final long transportGeneration;
        final long decoderGeneration;
        final long presentationGeneration;
        final long modelParentGeneration;
        final long modelChildGeneration;
        final long modelPresentationGeneration;
        final int receiverPid;
        final int producerPid;
        final long deliveredFrames;
        final boolean candidateEnabled;
        final boolean visible;
        final String suggestion;
        final String selectedContext;
        final int width;
        final int height;

        Snapshot(Type111ControlPlane plane) {
            state = plane.state;
            sessionId = plane.sessionId;
            connectionId = plane.identity == null ? 0L : plane.identity.connectionId;
            transportGeneration = plane.identity == null ? 0L : plane.identity.streamGeneration;
            decoderGeneration = plane.decoderGeneration;
            presentationGeneration = plane.presentationGeneration;
            NegotiatedType111Lifecycle.Snapshot lifecycle = plane.lifecycle.snapshot();
            modelParentGeneration = lifecycle.parentGeneration;
            modelChildGeneration = lifecycle.childGeneration;
            modelPresentationGeneration = lifecycle.presentationGeneration;
            receiverPid = lifecycle.receiverPid;
            producerPid = lifecycle.producerPid;
            deliveredFrames = lifecycle.deliveredFrames;
            candidateEnabled = lifecycle.candidateEnabled;
            visible = plane.visible;
            suggestion = plane.suggestion;
            selectedContext = plane.selectedContext;
            width = plane.videoWidth;
            height = plane.videoHeight;
        }
    }

    final long sessionId;
    final NegotiatedType111Lifecycle lifecycle;
    private String state = "SESSION_AVAILABLE";
    private Capability capability;
    private FrameStreamIdentity pendingIdentity;
    private FrameStreamIdentity identity;
    private String navigationProvider;
    private boolean navigationActive;
    private boolean instructionActive;
    private boolean visible;
    private String suggestion;
    private String selectedContext;
    private long decoderGeneration;
    private long presentationGeneration;
    private int videoWidth;
    private int videoHeight;
    private int[] viewArea;
    private int[] safeArea;

    Type111ControlPlane(FrameStreamIdentity parentOwner) {
        if (parentOwner == null || !parentOwner.isValid() ||
                parentOwner.streamType != FrameStreamIdentity.TYPE110)
            throw new IllegalArgumentException("invalid_type111_parent_owner");
        this.sessionId = parentOwner.sessionId;
        this.lifecycle = new NegotiatedType111Lifecycle(parentOwner);
    }

    synchronized String registerCapability(Capability value) {
        if (value == null || value.sessionId != sessionId || capability != null ||
                !"SESSION_AVAILABLE".equals(state)) return "capability_registration_rejected";
        String candidate = lifecycle.enableCandidate();
        if (!"accepted".equals(candidate)) return candidate;
        capability = value;
        state = "SECONDARY_CAPABILITY_REGISTERED";
        return "accepted";
    }

    synchronized String setup(FrameStreamIdentity value) {
        if (capability == null || !"SECONDARY_CAPABILITY_REGISTERED".equals(state) ||
                value == null || !value.isValid() || value.streamType != FrameStreamIdentity.TYPE111 ||
                value.sessionId != sessionId) return "type111_setup_rejected";
        String result = lifecycle.setup(value);
        if (!"accepted".equals(result)) return result;
        pendingIdentity = value;
        state = "TYPE111_SETUP_PENDING";
        return "accepted";
    }

    synchronized String activate(FrameStreamIdentity value, int receiverPid) {
        if (!"TYPE111_SETUP_PENDING".equals(state) || pendingIdentity == null ||
                !pendingIdentity.equals(value)) return "type111_setup_identity_mismatch";
        String result = lifecycle.activate(value, receiverPid);
        if (!"accepted".equals(result)) return result;
        identity = value;
        pendingIdentity = null;
        videoWidth = capability.width;
        videoHeight = capability.height;
        decoderGeneration = 1L;
        state = "TYPE111_STREAM_ACTIVE";
        return "accepted";
    }

    synchronized String navigation(FrameStreamIdentity requestIdentity, String provider,
            boolean active, boolean instruction) {
        if (!matchesActive(requestIdentity)) return "stale_or_inactive_type111";
        if (!active) {
            lifecycle.presentation(requestIdentity, false);
            navigationProvider = null;
            navigationActive = false;
            instructionActive = false;
            clearSelection();
            state = "NAVIGATION_PRESENTATION_HIDDEN";
            return "accepted";
        }
        if (identity == null || (!"maps".equals(provider) && !"waze".equals(provider)))
            return "unsupported_navigation_provider";
        navigationProvider = provider;
        navigationActive = true;
        instructionActive = instruction;
        if (suggestion != null && !eligible(suggestion)) clearSelection();
        return "accepted";
    }

    synchronized String presentation(FrameStreamIdentity requestIdentity, String command, String context) {
        if (!matchesActive(requestIdentity)) return "stale_or_inactive_type111";
        if ("suggestUI".equals(command)) {
            if (context == null || !eligible(context)) return "ui_context_not_eligible";
            suggestion = context;
            return "accepted";
        }
        if ("showUI".equals(command)) {
            if (suggestion == null || !eligible(suggestion)) return "no_eligible_ui_suggestion";
            String lifecycleResult = lifecycle.presentation(requestIdentity, true);
            if (!"accepted".equals(lifecycleResult)) return lifecycleResult;
            if (!visible || !suggestion.equals(selectedContext)) presentationGeneration++;
            selectedContext = suggestion;
            visible = true;
            state = "NAVIGATION_PRESENTATION_ACTIVE";
            return "accepted";
        }
        if ("stopUI".equals(command)) {
            String lifecycleResult = lifecycle.presentation(requestIdentity, false);
            if (!"accepted".equals(lifecycleResult)) return lifecycleResult;
            clearSelection();
            state = "NAVIGATION_PRESENTATION_HIDDEN";
            return "accepted";
        }
        return "unsupported_presentation_command";
    }

    synchronized String geometry(FrameStreamIdentity requestIdentity, int[] area, boolean safe) {
        if (!matchesActive(requestIdentity) || area == null || area.length != 4)
            return "invalid_geometry_request";
        int left = area[0], top = area[1], right = area[2], bottom = area[3];
        if (left < 0 || top < 0 || right <= left || bottom <= top ||
                right > capability.width || bottom > capability.height) return "geometry_out_of_bounds";
        if (safe) {
            if (viewArea != null && !contains(viewArea, area)) return "safe_area_outside_view_area";
            safeArea = copy(area);
        } else {
            if (safeArea != null && !contains(area, safeArea)) return "view_area_excludes_safe_area";
            viewArea = copy(area);
        }
        presentationGeneration++;
        return "accepted";
    }

    synchronized String videoConfig(FrameStreamIdentity requestIdentity, int width, int height) {
        if (!matchesActive(requestIdentity)) return "stale_or_inactive_type111";
        if (width <= 0 || height <= 0 || width > 1920 || height > 1080 ||
                (long) width * (long) height * 4L > FrameIpcProtocol.MAX_FRAME_BYTES)
            return "invalid_video_config";
        long nextDecoderGeneration = decoderGeneration + 1L;
        String lifecycleResult = lifecycle.decoderReady(requestIdentity, nextDecoderGeneration, width, height);
        if (!"accepted".equals(lifecycleResult)) return lifecycleResult;
        videoWidth = width;
        videoHeight = height;
        decoderGeneration = nextDecoderGeneration;
        return "accepted";
    }

    synchronized String transportGeneration(FrameStreamIdentity oldIdentity, FrameStreamIdentity newIdentity,
            int receiverPid) {
        if (!canTransportGeneration(oldIdentity, newIdentity)) return "invalid_transport_generation";
        String lifecycleResult = lifecycle.transportGeneration(oldIdentity, newIdentity, receiverPid);
        if (!"accepted".equals(lifecycleResult)) return lifecycleResult;
        identity = newIdentity;
        videoWidth = capability.width;
        videoHeight = capability.height;
        decoderGeneration++;
        clearSelection();
        state = "TYPE111_STREAM_ACTIVE";
        return "accepted";
    }

    synchronized boolean canTransportGeneration(FrameStreamIdentity oldIdentity,
            FrameStreamIdentity newIdentity) {
        return matchesActive(oldIdentity) && newIdentity != null && newIdentity.isValid() &&
                newIdentity.sessionId == sessionId &&
                newIdentity.streamType == FrameStreamIdentity.TYPE111 &&
                newIdentity.connectionId == oldIdentity.connectionId &&
                newIdentity.outputId == oldIdentity.outputId &&
                newIdentity.streamGeneration > oldIdentity.streamGeneration;
    }

    synchronized String teardown(FrameStreamIdentity requestIdentity) {
        if (identity == null || requestIdentity == null || !identity.equals(requestIdentity))
            return "stale_type111_teardown";
        String lifecycleResult = lifecycle.withdrawChild(requestIdentity);
        if (!"accepted".equals(lifecycleResult)) return lifecycleResult;
        identity = null;
        pendingIdentity = null;
        videoWidth = 0;
        videoHeight = 0;
        decoderGeneration = 0L;
        viewArea = null;
        safeArea = null;
        clearSelection();
        state = capability == null ? "SESSION_AVAILABLE" : "SECONDARY_CAPABILITY_REGISTERED";
        return "accepted";
    }

    synchronized Snapshot snapshot() { return new Snapshot(this); }

    synchronized void parentTeardown() {
        lifecycle.parentTeardown();
        identity = null;
        pendingIdentity = null;
        capability = null;
        videoWidth = 0;
        videoHeight = 0;
        decoderGeneration = 0L;
        viewArea = null;
        safeArea = null;
        clearSelection();
        state = "TEARDOWN";
    }

    synchronized String producerBound(FrameStreamIdentity requestIdentity, int pid) {
        return lifecycle.producerBound(requestIdentity, pid);
    }

    synchronized String producerDied(FrameStreamIdentity requestIdentity, int pid) {
        String result = lifecycle.producerDied(requestIdentity, pid);
        if ("accepted".equals(result)) {
            decoderGeneration = 0L;
            videoWidth = 0;
            videoHeight = 0;
            clearSelection();
            state = "TYPE111_STREAM_ACTIVE";
        }
        return result;
    }

    synchronized String producerBindFailed(FrameStreamIdentity requestIdentity, int pid) {
        String result = lifecycle.producerBindFailed(requestIdentity, pid);
        if ("accepted".equals(result)) {
            decoderGeneration = 0L;
            videoWidth = 0;
            videoHeight = 0;
            clearSelection();
            state = "TYPE111_STREAM_ACTIVE";
        }
        return result;
    }

    synchronized String frameDelivered(FrameStreamIdentity requestIdentity, long frameId) {
        return lifecycle.frameDelivered(requestIdentity, frameId);
    }

    private boolean matchesActive(FrameStreamIdentity value) {
        return identity != null && identity.equals(value) &&
                ("TYPE111_STREAM_ACTIVE".equals(state) ||
                "NAVIGATION_PRESENTATION_ACTIVE".equals(state) ||
                "NAVIGATION_PRESENTATION_HIDDEN".equals(state));
    }

    private boolean eligible(String context) {
        return capability != null && navigationActive && navigationProvider != null &&
                capability.contexts.contains(context) &&
                (!INSTRUCTION_CONTEXT.equals(context) || instructionActive);
    }

    private void clearSelection() {
        if (visible || suggestion != null || selectedContext != null) presentationGeneration++;
        visible = false;
        suggestion = null;
        selectedContext = null;
    }

    private static boolean validContexts(Set<String> contexts) {
        for (String context : contexts) {
            if (!MAP_CONTEXT.equals(context) && !INSTRUCTION_CONTEXT.equals(context)) return false;
        }
        return true;
    }

    private static boolean contains(int[] outer, int[] inner) {
        return inner[0] >= outer[0] && inner[1] >= outer[1] &&
                inner[2] <= outer[2] && inner[3] <= outer[3];
    }

    private static int[] copy(int[] value) {
        return new int[] { value[0], value[1], value[2], value[3] };
    }
}
