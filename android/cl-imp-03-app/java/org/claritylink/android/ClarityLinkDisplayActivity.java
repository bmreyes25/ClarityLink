package org.claritylink.android;

import android.app.Activity;
import android.content.Context;
import android.content.ComponentName;
import android.content.Intent;
import android.content.ServiceConnection;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.hardware.display.DisplayManager;
import android.os.Binder;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.Parcel;
import android.os.RemoteException;
import android.os.SystemClock;
import android.util.Log;
import android.util.Base64;
import android.view.Display;
import android.view.Surface;
import android.view.View;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.TextView;

import org.claritylink.renderer.ClarityLinkContentView;
import org.claritylink.renderer.DecodedFrame;
import org.claritylink.renderer.DiagnosticFrameSource;
import org.claritylink.renderer.Display1OutputBackend;
import org.claritylink.renderer.FrameSource;
import org.claritylink.renderer.RendererViewport;

import java.nio.ByteBuffer;
import java.io.File;
import java.io.FileOutputStream;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/** Standalone API17 adapter. Display admission is emulator-only and opt-in per launch. */
public final class ClarityLinkDisplayActivity extends Activity
        implements SecondaryDisplayHost.HostedContentListener {
    private static final class FixtureRunToken {
        private boolean cancelled;
        private boolean teardownClaimed;
        synchronized boolean isCancelled() { return cancelled; }
        synchronized boolean cancelForDetach() {
            if (teardownClaimed) return false;
            cancelled = true;
            return true;
        }
        synchronized boolean claimTeardown() {
            if (cancelled || teardownClaimed) return false;
            teardownClaimed = true;
            return true;
        }
    }
    private static final String TAG = "ClarityLinkCLIMP03";
    private static final String EXTRA_MODE = "mode";
    private static final String EXTRA_CONFIRM = "emulator_only_confirmation";
    private static final String EXTRA_CRASH = "crash_after_first_frame";
    private static final String EXTRA_CONTROLLED_EXIT = "controlled_exit_after_validation";
    private static final String EXTRA_TYPE111_FIXTURE = "type111_fixture_mode";
    private static final String EXTRA_TYPE111_FIRST = "type111_first_mode";
    private static final String EXTRA_REATTACH_SESSION_ID = "type111_reattach_session_id";
    private static final String EXTRA_REATTACH_TEST = "type111_reattach_test";
    private static final String EXTRA_OWNER_DEATH_TEST = "owner_death_test";
    private static final String EXTRA_REENTRANT_TEARDOWN_TEST = "reentrant_teardown_test";
    private static final String EXTRA_DELAYED_DEATH_CALLBACK_TEST = "delayed_death_callback_test";
    private static final String EXTRA_SECURITY_LIVE_PRODUCER = "security_live_producer";
    private static final String LAB_MODE = "EMULATOR_PRESENTATION";
    private static final String LAB_CONFIRM = "CL_IMP_03_OFFLINE_EMULATOR_ONLY";
    private static final boolean PRODUCTION_HONDA_INTEGRATION_ENABLED = false;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final FrameViewSink viewSink = new FrameViewSink(main, new FrameViewSink.Target() {
        public boolean enqueue(DecodedFrame frame, long generation, long frameId, long dispatchEpoch) {
            FrameStreamIdentity identity = frameIpcClient == null ? null : frameIpcClient.streamIdentity();
            if (!active || closing || identity == null || identity.streamGeneration != generation ||
                    renderer == null) return false;
            try {
                renderer.submit(frame, viewSink.dispatchGate(), generation, dispatchEpoch);
                log("BINDER_FRAME_SUBMITTED_TO_CONTENT_VIEW generation=" + generation +
                        " frame_id=" + frameId + " timestamp_ns=" + frame.presentationTimeNs);
                FrameViewSink.TestControl control = warningRaceControl;
                if (control != null && frame.presentationTimeNs == control.recoveryTimestamp) {
                    awaitRaceRecoveryFrame(0, generation, frame.presentationTimeNs);
                } else {
                    boolean warningRaceFrame = control != null &&
                            control.beforeViewSubmit(frame.presentationTimeNs);
                    if (!warningRaceFrame) awaitFrame(0, generation, frame.presentationTimeNs);
                }
                return true;
            } catch (RuntimeException failure) {
                log("BINDER_FRAME_VIEW_SUBMIT_FAILED type=" + failure.getClass().getSimpleName());
                return false;
            }
        }

        public boolean setWarningVisible(long generation, boolean visible) {
            FrameStreamIdentity identity = frameIpcClient == null ? null : frameIpcClient.streamIdentity();
            if (!active || closing || identity == null || identity.streamGeneration != generation ||
                    renderer == null) return false;
            ClarityLinkContentView view = renderer.contentView();
            if (view == null) return false;
            if (visible) view.onHostSuspended(HostedContentLifecycle.WARNING_PREEMPTION, activeGeneration);
            else view.onHostResumed(activeGeneration);
            FrameViewSink.TestControl control = warningRaceControl;
            if (control != null) control.warningApplied(visible);
            return true;
        }

        public boolean replaceGeneration(final long oldGeneration, final long newGeneration) {
            final CountDownLatch completed = new CountDownLatch(1);
            final boolean[] accepted = new boolean[] { false };
            main.post(new Runnable() {
                public void run() {
                    try {
                        FrameStreamIdentity identity = frameIpcClient == null ? null : frameIpcClient.streamIdentity();
                        if (active && !closing && identity != null &&
                                identity.streamGeneration == oldGeneration && renderer != null) {
                            renderer.clear();
                            accepted[0] = true;
                            log("VIEW_STREAM_GENERATION_REPLACED old=" + oldGeneration +
                                    " new=" + newGeneration + " parent_display_generation=" +
                                    activeGeneration + " view_instance_preserved=true");
                        }
                    } catch (RuntimeException failure) {
                        log("VIEW_SESSION_GENERATION_REJECT type=" + failure.getClass().getSimpleName());
                    } finally { completed.countDown(); }
                }
            });
            try {
                return completed.await(5L, TimeUnit.SECONDS) && accepted[0];
            } catch (InterruptedException interrupted) {
                Thread.currentThread().interrupt();
                return false;
            }
        }
    });
    private SecondaryDisplayHost displayHost;
    private Display1OutputBackend renderer;
    private FrameLayout presentationRoot;
    private TextView status;
    private Surface borrowedPresentationSurface;
    private long activeGeneration;
    private boolean active;
    private boolean closing;
    private boolean recreation;
    private boolean crashAfterFirstFrame;
    private boolean controlledExitAfterValidation;
    private boolean type111FixtureMode;
    private boolean type111FirstMode;
    private long reattachSessionId;
    private long reattachType110Generation;
    private long fixtureTimestampOffsetNs;
    private long lastType111SubmissionTimestampNs;
    private boolean type111ReattachTest;
    private boolean ownerDeathTest;
    private boolean reentrantTeardownTest;
    private volatile boolean reentrantTeardownInProgress;
    private boolean delayedDeathCallbackTest;
    private boolean type110SinkFailureTest;
    private ServiceConnection securityProducerConnection;
    private boolean securityProducerBound;
    private boolean type111RunStarted;
    private volatile Thread type111FixtureWorker;
    private volatile FixtureRunToken type111FixtureRunToken;
    private boolean compositorBound;
    private boolean ipcSessionReady;
    private boolean ipcSubmitted;
    private boolean canvasDrawLogged;
    private boolean rendererScenarioValidated;
    private boolean warningResumeValidated;
    private boolean diagnosticRunStarted;
    private int diagnosticFrameIndex;
    private long lastDiagnosticDrawTimestampNs = -1L;
    private FrameSource staticDiagnosticSource;
    private FrameSource syntheticDiagnosticSource;
    private FrameViewSink.TestControl warningRaceControl;
    private boolean warningRaceStarted;
    private FrameIpcClient frameIpcClient;
    private FrameIpcClient primaryLabIpcClient;
    private Type111ControlClient type111ControlClient;
    private IBinder primaryLabSinkBinder;
    private IBinder compositorEndpoint;
    private IBinder observedCompositorBinder;
    private IBinder.DeathRecipient compositorDeathRecipient;
    private boolean primarySinkBound;
    private boolean compositorServiceStarted;
    private boolean type110SinkServiceStarted;
    private boolean type110SinkStartAttempted;
    private boolean ipcSessionStartAttempted;
    private boolean parentSessionPreservedForLifecycle;
    private volatile boolean parentOwnerLost;
    private volatile long parentOwnerLossSessionId;
    private volatile boolean parentOwnerLossWhileDetached;
    private boolean lifecycleReattachPending;
    private int compositorRemotePid = -1;
    private final ServiceConnection primarySinkConnection = new ServiceConnection() {
        public void onServiceConnected(ComponentName name, IBinder service) {
            primaryLabSinkBinder = service;
            startIpcSessionWhenReady();
        }
        public void onServiceDisconnected(ComponentName name) {
            primaryLabSinkBinder = null;
            if (active && !closing && !reentrantTeardownInProgress)
                stopOwnedDisplay("type110-lab-sink-disconnected");
            else if (reentrantTeardownInProgress)
                log("CL_R4B_TYPE110_DEATH_DURING_TEARDOWN_CLEANUP_DEFERRED=true");
        }
    };
    private final ServiceConnection compositorConnection = new ServiceConnection() {
        public void onServiceConnected(ComponentName name, android.os.IBinder service) {
            if (active && ipcSessionReady && compositorRemotePid > 0 &&
                    primaryLabSinkBinder != null) {
                try {
                    FrameStreamIdentity owner = FrameLabSink.queryIdentity(primaryLabSinkBinder);
                    Type111ControlClient.StreamQuery rebound = owner == null ? null :
                            new Type111ControlClient(service).queryType111Stream(owner);
                    if (rebound == null || !rebound.ownerValid ||
                            rebound.compositorPid != compositorRemotePid) {
                        compositorEndpoint = service;
                        log("CL_R4B_ACTIVITY_OWNER_INVALIDATED old_pid=" + compositorRemotePid +
                                " new_pid=" + (rebound == null ? -1 : rebound.compositorPid) +
                                " session_id=" + (owner == null ? 0L : owner.sessionId) +
                                " old_session_reused=false");
                        parentOwnerLossSessionId = activeGeneration;
                        parentOwnerLost = true;
                        stopOwnedDisplay("parent-owner-replaced");
                        return;
                    }
                } catch (Exception failure) {
                    compositorEndpoint = service;
                    log("CL_R4B_ACTIVITY_OWNER_INVALIDATED old_pid=" + compositorRemotePid +
                            " new_pid=-1 session_id=unknown old_session_reused=false reason=" +
                            failure.getClass().getSimpleName());
                    parentOwnerLossSessionId = activeGeneration;
                    parentOwnerLost = true;
                    stopOwnedDisplay("parent-owner-replaced");
                    return;
                }
            }
            compositorEndpoint = service;
            observeCompositorBinder(service);
            if (!startAuthorizedType110Sink(service)) return;
            startIpcSessionWhenReady();
        }
        public void onServiceDisconnected(ComponentName name) {
            final int lostPid = compositorRemotePid;
            final long lostSession = activeGeneration;
            compositorEndpoint = null;
            frameIpcClient = null;
            ipcSessionReady = false;
            log("IPC_REMOTE_DISCONNECTED");
            if (active && !closing) {
                log("CL_R4B_ACTIVITY_OWNER_INVALIDATED old_pid=" + lostPid +
                        " new_pid=-1 session_id=" + lostSession +
                        " old_session_reused=false notification=binder-disconnected");
                parentOwnerLossSessionId = lostSession;
                parentOwnerLost = true;
                stopOwnedDisplay("parent-owner-died");
            }
        }
    };

    private void observeCompositorBinder(final IBinder binder) {
        if (binder == null) return;
        if (compositorDeathRecipient != null && observedCompositorBinder != null) {
            try { observedCompositorBinder.unlinkToDeath(compositorDeathRecipient, 0); }
            catch (RuntimeException ignored) { }
        }
        final long observedSessionId = activeGeneration;
        observedCompositorBinder = binder;
        compositorDeathRecipient = new IBinder.DeathRecipient() {
            public void binderDied() {
                if (observedCompositorBinder != binder) return;
                parentOwnerLossSessionId = observedSessionId;
                parentOwnerLossWhileDetached = !active;
                parentOwnerLost = true;
                log("CL_R4B_ACTIVITY_OWNER_INVALIDATED old_pid=" + compositorRemotePid +
                        " new_pid=-1 session_id=" + observedSessionId +
                        " old_session_reused=false notification=binder-death-recipient");
                main.post(new Runnable() {
                    public void run() {
                        if (parentOwnerLossSessionId != activeGeneration || !active || closing) return;
                        stopOwnedDisplay("parent-owner-died");
                    }
                });
            }
        };
        try { binder.linkToDeath(compositorDeathRecipient, 0); }
        catch (android.os.RemoteException alreadyDead) {
            if (active && !closing) {
                log("CL_R4B_ACTIVITY_OWNER_INVALIDATED old_pid=" + compositorRemotePid +
                        " new_pid=-1 session_id=" + activeGeneration +
                        " old_session_reused=false notification=already-dead-binder");
                parentOwnerLossSessionId = activeGeneration;
                parentOwnerLost = true;
                stopOwnedDisplay("parent-owner-died");
            }
        }
    }

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        type111FixtureMode = getIntent() != null && getIntent().getBooleanExtra(EXTRA_TYPE111_FIXTURE, false);
        type111FirstMode = getIntent() != null && getIntent().getBooleanExtra(EXTRA_TYPE111_FIRST, false);
        reattachSessionId = getIntent() == null ? 0L :
                getIntent().getLongExtra(EXTRA_REATTACH_SESSION_ID, 0L);
        type111ReattachTest = getIntent() != null && getIntent().getBooleanExtra(EXTRA_REATTACH_TEST, false);
        ownerDeathTest = getIntent() != null && getIntent().getBooleanExtra(EXTRA_OWNER_DEATH_TEST, false);
        reentrantTeardownTest = getIntent() != null &&
                getIntent().getBooleanExtra(EXTRA_REENTRANT_TEARDOWN_TEST, false);
        delayedDeathCallbackTest = getIntent() != null &&
                getIntent().getBooleanExtra(EXTRA_DELAYED_DEATH_CALLBACK_TEST, false);
        type110SinkFailureTest = getIntent() != null &&
                getIntent().getBooleanExtra("type110_sink_failure_test", false);
        recreation = state != null;
        showStatus("ClarityLink disabled candidate. No display is selected automatically.");
        log("ACTIVITY_READY api=" + Build.VERSION.SDK_INT + " pid=" + android.os.Process.myPid()
                + " permissions_requested=none");
        if (!recreation && isExplicitLabRequest(getIntent().getExtras())) startEmulatorLab();
        else log("STATUS_ONLY feature_disabled=true recovered_state=discarded");
    }

    private void startIpcSessionWhenReady() {
        if (!active || closing || activeGeneration <= 0 || ipcSessionStartAttempted ||
                compositorEndpoint == null || primaryLabSinkBinder == null) return;
        ipcSessionStartAttempted = true;
        FrameIpcClient client = new FrameIpcClient(compositorEndpoint);
        FrameIpcClient primaryClient = new FrameIpcClient(compositorEndpoint);
        try {
            FrameStreamIdentity primaryIdentity = FrameLabSink.queryIdentity(primaryLabSinkBinder);
            if (primaryIdentity == null || primaryIdentity.streamType != FrameStreamIdentity.TYPE110 ||
                    primaryIdentity.sessionId != activeGeneration)
                throw new IllegalStateException("existing_type110_owner_identity_unavailable");
            FrameStreamIdentity secondaryIdentity = new FrameStreamIdentity(activeGeneration,
                    FrameStreamIdentity.TYPE111, 11101L, activeGeneration,
                    FrameStreamIdentity.OUTPUT_SECONDARY_VIEW);
            Type111ControlClient control = new Type111ControlClient(compositorEndpoint);
            type111ControlClient = control;
            if (reattachSessionId <= 0L) {
                requireType111(!control.registerLabCapability(primaryIdentity,
                        "claritylink-api17-secondary", 800, 480, 30),
                        "ownerless_type111_capability_rejected");
                Type111ControlClient.StreamQuery ownerlessState =
                        control.queryType111Stream(primaryIdentity);
                requireType111(ownerlessState != null && !ownerlessState.ownerValid &&
                        ownerlessState.identity == null && !ownerlessState.sinkAttached,
                        "ownerless_capability_has_no_stream_state");
                Log.i(TAG, "CL_R4B_OWNERLESS_CAPABILITY_REJECTED session_id=" +
                        primaryIdentity.sessionId + " owner_authority_open=false owner_stream_registered=false " +
                        "type111_state_created=false query_valid=false");
            }
            if (!FrameIpcClient.openParentAuthority(compositorEndpoint, primaryIdentity,
                    primaryLabSinkBinder))
                throw new IllegalStateException("type110_parent_authority_open_rejected");
            int primaryRemotePid;
            int remotePid;
            Type111ControlClient.StreamQuery existing = reattachSessionId > 0L ?
                    control.queryType111Stream(primaryIdentity) : null;
            if (reattachSessionId > 0L && (existing == null || !existing.ownerValid))
                throw new IllegalStateException("type111_owner_query_rejected");
            if (existing != null && existing.identity != null && existing.sinkAttached &&
                    lifecycleReattachPending) {
                if (!control.detachType111Sink(primaryIdentity, existing.identity)) {
                    ipcSessionStartAttempted = false;
                    main.postDelayed(new Runnable() {
                        public void run() { startIpcSessionWhenReady(); }
                    }, 100L);
                    log("TYPE111_LIFECYCLE_DETACH_DEFERRED transfer_in_flight=true retry_ms=100");
                    return;
                }
                existing = control.queryType111Stream(primaryIdentity);
                if (existing == null || !existing.ownerValid || existing.sinkAttached)
                    throw new IllegalStateException("type111_lifecycle_detach_not_observed");
            }
            if (existing != null && existing.identity != null) {
                if (existing.sinkAttached && !delayedDeathCallbackTest)
                    throw new IllegalStateException("active_type111_stream_cannot_be_replaced");
                FrameStreamIdentity replacement = existing.identity.withGeneration(
                        existing.identity.streamGeneration + 1L);
                reattachType110Generation = primaryIdentity.streamGeneration;
                viewSink.begin(replacement);
                if (!FrameIpcClient.replaceType111Sink(compositorEndpoint, primaryIdentity,
                        existing.identity, replacement, viewSink))
                    throw new IllegalStateException("type111_sink_replacement_rejected");
                client = FrameIpcClient.attachExistingType111(compositorEndpoint, replacement, 1L);
                String staleFrame = client == null ? "client_unavailable" :
                        client.probeMalformed("stale_generation", existing.identity.streamGeneration,
                                SystemClock.elapsedRealtimeNanos());
                if (!"frame_contract_rejected".equals(staleFrame))
                    throw new IllegalStateException("stale_type111_frame_not_rejected");
                FrameLabSink.Stats stats = FrameLabSink.queryStats(primaryLabSinkBinder);
                primaryClient = stats == null ? null : FrameIpcClient.attachExistingType110(
                        compositorEndpoint, primaryIdentity, stats.frameId + 1L);
                if (client == null || primaryClient == null)
                    throw new IllegalStateException("reattached_stream_client_unavailable");
                if (delayedDeathCallbackTest) {
                    FrameStreamIdentity wrongOwner = new FrameStreamIdentity(
                            primaryIdentity.sessionId + 1L, primaryIdentity.streamType,
                            primaryIdentity.connectionId, primaryIdentity.streamGeneration,
                            primaryIdentity.outputId);
                    FrameStreamIdentity wrongChild = replacement.withGeneration(
                            replacement.streamGeneration + 1L);
                    requireType111(!control.fireLabDelayedSinkDeathCallback(wrongOwner, replacement),
                            "wrong_owner_callback_release_rejected");
                    requireType111(!control.fireLabDelayedSinkDeathCallback(primaryIdentity, wrongChild),
                            "wrong_generation_callback_release_rejected");
                    Type111ControlClient.StreamQuery afterRejectedReleases =
                            control.queryType111Stream(primaryIdentity);
                    requireType111(afterRejectedReleases != null && afterRejectedReleases.identity != null &&
                            replacement.equals(afterRejectedReleases.identity) && afterRejectedReleases.sinkAttached,
                            "rejected_callback_release_preserved_replacement");
                    Log.i(TAG, "CL_R4B_DELAYED_CALLBACK_NEGATIVE_IDENTITY_PASS wrong_session=true " +
                            "wrong_generation=true replacement_unchanged=true");
                    if (!control.fireLabDelayedSinkDeathCallback(primaryIdentity, replacement))
                        throw new IllegalStateException("delayed_old_sink_callback_changed_replacement");
                    requireType111(!control.fireLabDelayedSinkDeathCallback(primaryIdentity, replacement),
                            "duplicate_callback_release_rejected");
                    Type111ControlClient.StreamQuery afterDelayedCallback =
                            control.queryType111Stream(primaryIdentity);
                    if (afterDelayedCallback == null || afterDelayedCallback.identity == null ||
                            !replacement.equals(afterDelayedCallback.identity) || !afterDelayedCallback.sinkAttached)
                        throw new IllegalStateException("replacement_sink_lost_after_delayed_old_callback");
                    Log.i(TAG, "CL_R4B_DELAYED_SINK_CALLBACK_PASS session_id=" + replacement.sessionId +
                            " old_generation=" + existing.identity.streamGeneration +
                            " new_generation=" + replacement.streamGeneration +
                            " old_callback_completed_after_replacement=true replacement_preserved=true");
                }
                remotePid = existing.compositorPid;
                primaryRemotePid = remotePid;
                log("CL_R4A_TYPE111_SINK_REPLACED session_id=" + activeGeneration +
                        " old_generation=" + existing.identity.streamGeneration +
                        " new_generation=" + replacement.streamGeneration +
                        " type110_generation=" + primaryIdentity.streamGeneration +
                        " compositor_pid=" + remotePid + " authorized_type110_owner=true " +
                        "stale_frame_rejected=true");
            } else {
                if (reattachSessionId > 0L)
                    throw new IllegalStateException("type111_existing_stream_unavailable_for_reattach");
                boolean capability = control.registerLabCapability(primaryIdentity,
                        "claritylink-api17-secondary", 800, 480, 30);
                boolean setup = capability && control.setup(secondaryIdentity);
                if (!setup) throw new IllegalStateException("type111_lab_setup_rejected");
                requireType111(!control.registerLabCapability(primaryIdentity,
                        "claritylink-api17-secondary", 800, 480, 30),
                        "duplicate_secondary_capability_rejected");
                requireType111(!control.setup(secondaryIdentity), "duplicate_pending_setup_rejected");
                viewSink.begin(secondaryIdentity);
                if (type111FirstMode) {
                    remotePid = client.begin(secondaryIdentity, viewSink);
                    primaryRemotePid = primaryClient.begin(primaryIdentity, primaryLabSinkBinder);
                } else {
                    primaryRemotePid = primaryClient.begin(primaryIdentity, primaryLabSinkBinder);
                    remotePid = client.begin(secondaryIdentity, viewSink);
                }
            }
            if (remotePid <= 0 || remotePid == android.os.Process.myPid() || primaryRemotePid != remotePid) {
                log("IPC_SESSION_REJECTED separate_process_required=true");
                if (remotePid > 0) client.end(activeGeneration);
                if (primaryRemotePid > 0) primaryClient.end(activeGeneration);
                stopOwnedDisplay("ipc-session-start-failed");
                return;
            }
            frameIpcClient = client;
            primaryLabIpcClient = primaryClient;
            compositorRemotePid = remotePid;
            ipcSessionReady = true;
            if (lifecycleReattachPending && !type111ReattachTest) {
                reattachSessionId = 0L;
                lifecycleReattachPending = false;
            }
            FrameLabSink.Stats sinkStats = FrameLabSink.queryStats(primaryLabSinkBinder);
            if (sinkStats == null || sinkStats.pid == android.os.Process.myPid())
                throw new IllegalStateException("type110_sink_process_not_isolated");
            log("IPC_SESSION_STARTED generation=" + activeGeneration + " remote_pid=" + remotePid
                    + " type111_view_pid=" + android.os.Process.myPid() + " type110_sink_pid=" +
                    sinkStats.pid + " type110_sink_uid=" + sinkStats.uid + " " +
                    "streams=110:primary_lab,111:secondary_view " +
                    "setup_order=" + (type111FirstMode ? "111_first" : "110_first") + " " +
                    "transport=stream_identity_private_binder_pfd_then_reverse_binder_pfd_to_output " +
                    "pixel_format=RGBA_8888 max_frame_bytes=4194304");
            if (renderer != null) {
                if (reattachSessionId > 0L && type111FixtureMode)
                    startType111FixtureRun(activeGeneration);
                else submitSyntheticFrame(activeGeneration);
            }
        } catch (Exception failure) {
            log("IPC_SESSION_REJECTED type=" + failure.getClass().getSimpleName());
            Log.e(TAG, "IPC_SESSION_REJECTED_DETAIL", failure);
            stopOwnedDisplay("ipc-session-start-failed");
        }
    }

    private void showStatus(String message) {
        FrameLayout root = new FrameLayout(this);
        status = new TextView(this);
        status.setTextColor(Color.WHITE);
        status.setTextSize(16.0f);
        status.setPadding(24, 24, 24, 24);
        status.setText(message);
        root.addView(status, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.WRAP_CONTENT));
        Button lab = new Button(this);
        lab.setText("Start emulator display lab");
        lab.setOnClickListener(new View.OnClickListener() {
            public void onClick(View view) {
                if (isEmulator()) startEmulatorLab();
                else setStatus("Display lab is restricted to an API17 emulator.");
            }
        });
        FrameLayout.LayoutParams button = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.WRAP_CONTENT, FrameLayout.LayoutParams.WRAP_CONTENT);
        button.topMargin = 128;
        root.addView(lab, button);
        setContentView(root);
    }

    private void setStatus(String message) {
        if (status != null) status.setText(message);
        log(message.replace(' ', '_'));
    }

    private boolean isExplicitLabRequest(Bundle extras) {
        return extras != null && LAB_MODE.equals(extras.getString(EXTRA_MODE)) &&
                LAB_CONFIRM.equals(extras.getString(EXTRA_CONFIRM));
    }

    private boolean isEmulator() {
        String hardware = Build.HARDWARE == null ? "" : Build.HARDWARE.toLowerCase();
        String fingerprint = Build.FINGERPRINT == null ? "" : Build.FINGERPRINT.toLowerCase();
        return hardware.contains("goldfish") || hardware.contains("ranchu") ||
                fingerprint.startsWith("generic") || fingerprint.contains("emulator");
    }

    private void startEmulatorLab() {
        if (PRODUCTION_HONDA_INTEGRATION_ENABLED) {
            setStatus("Production Honda integration is disabled in this candidate.");
            return;
        }
        if (!isEmulator()) {
            setStatus("Emulator-only display admission refused.");
            return;
        }
        if (active || displayHost != null) stopOwnedDisplay("replace");
        Bundle launch = getIntent() == null ? null : getIntent().getExtras();
        crashAfterFirstFrame = launch != null && launch.getBoolean(EXTRA_CRASH, false);
        controlledExitAfterValidation = launch != null && launch.getBoolean(EXTRA_CONTROLLED_EXIT, false);
        DisplayDiscovery discovery;
        List<DisplayDiscovery.Info> inventory;
        try {
            discovery = new DisplayDiscovery(this);
            inventory = discovery.enumerate();
        } catch (RuntimeException failure) {
            setStatus("Display discovery failed: " + failure.getClass().getSimpleName());
            return;
        }
        log("DISPLAY_ENUMERATION count=" + inventory.size());
        for (DisplayDiscovery.Info info : inventory)
            log("DISPLAY id=" + info.id + " valid=" + info.valid + " size=" + info.width + "x" + info.height);
        final Display selected;
        try {
            selected = discovery.select(new DisplayDiscovery.Selector() {
                public boolean matches(DisplayDiscovery.Info info) {
                    return info.valid && info.id != 0 && info.width == 800 && info.height == 480;
                }
            });
        } catch (RuntimeException failure) {
            setStatus("Display selection failed closed: " + failure.getClass().getSimpleName());
            return;
        }
        if (selected == null) {
            setStatus("No unique synthetic 800x480 emulator display; admission refused.");
            return;
        }
        ClarityLinkDisplayApplication application = (ClarityLinkDisplayApplication) getApplication();
        activeGeneration = reattachSessionId > 0L ? reattachSessionId : application.nextGeneration();
        // Reserve generation 1 so the first lab run can exercise a positive stale generation.
        if (reattachSessionId <= 0L && activeGeneration == 1L) activeGeneration = application.nextGeneration();
        active = true;
        closing = false;
        parentSessionPreservedForLifecycle = false;
        ipcSessionReady = false;
        ipcSessionStartAttempted = false;
        compositorEndpoint = null;
        primaryLabSinkBinder = null;
        ipcSubmitted = false;
        canvasDrawLogged = false;
        rendererScenarioValidated = false;
        warningResumeValidated = false;
        diagnosticRunStarted = false;
        diagnosticFrameIndex = 0;
        lastDiagnosticDrawTimestampNs = -1L;
        Intent compositorIntent = new Intent(this, CompositorService.class);
        compositorServiceStarted = startService(compositorIntent) != null;
        compositorBound = bindService(compositorIntent, compositorConnection, Context.BIND_AUTO_CREATE);
        if (!compositorServiceStarted || !compositorBound) {
            stopOwnedDisplay("ipc-bind-failed");
            return;
        }
        displayHost = new SecondaryDisplayHost(this);
        DisplayPolicy.Layout layout;
        try {
            layout = new DisplayPolicy.Layout(800, 480, 0, 0, 800, 480, 0, true);
        } catch (IllegalArgumentException invalid) {
            stopOwnedDisplay("invalid-lab-layout");
            return;
        }
        boolean shown = displayHost.showOfflineLabForRuntimeTest(this, selected, activeGeneration, layout);
        if (!shown) {
            stopOwnedDisplay("presentation-admission-failed");
            setStatus("Presentation admission failed closed.");
            return;
        }
        setStatus("SYNTHETIC API17 DISPLAY LAB — NOT CARPLAY — NOT HONDA INTEGRATION");
    }

    private boolean startAuthorizedType110Sink(IBinder compositor) {
        if (!active || closing || compositor == null) return false;
        if (type110SinkStartAttempted) return true;
        type110SinkStartAttempted = true;
        IBinder grant = null;
        if (reattachSessionId <= 0L) {
            try { grant = FrameIpcClient.requestType110SinkAdmission(compositor, activeGeneration); }
            catch (android.os.RemoteException unavailable) { }
            if (grant == null) {
                log("TYPE110_SINK_ADMISSION_REJECTED session_id=" + activeGeneration);
                stopOwnedDisplay("type110-sink-admission-failed");
                return false;
            }
        }
        if (reattachSessionId <= 0L) {
            long forgedSession = activeGeneration ^ 0x5a5a5a5a5a5a5a5aL;
            if (forgedSession <= 0L || forgedSession == activeGeneration) forgedSession = activeGeneration + 1L;
            Intent preclaim = new Intent(this, FrameLabSinkService.class);
            preclaim.putExtra(FrameLabSinkService.EXTRA_SESSION_ID, forgedSession);
            startService(preclaim);
            log("CL_R4B_SINK_OWNERLESS_PRECLAIM_ATTEMPT session_id=" + forgedSession +
                    " authorized_session_id=" + activeGeneration + " admission_attached=false");
        }
        Intent sinkIntent = new Intent(this, FrameLabSinkService.class);
        sinkIntent.putExtra(FrameLabSinkService.EXTRA_SESSION_ID, activeGeneration);
        if (grant != null) sinkIntent.putExtra(FrameLabSinkService.EXTRA_ADMISSION,
                new FrameLabSinkAdmission(activeGeneration, grant));
        type110SinkServiceStarted = startService(sinkIntent) != null;
        primarySinkBound = bindService(sinkIntent, primarySinkConnection, Context.BIND_AUTO_CREATE);
        if (!type110SinkServiceStarted || !primarySinkBound) {
            stopOwnedDisplay("ipc-bind-failed");
            return false;
        }
        log("TYPE110_SINK_ADMISSION_ACCEPTED session_id=" + activeGeneration +
                " compositor_bound=true grant=" + (grant != null));
        return true;
    }

    public void state(DisplayPolicy.Admission state) {
        log("ADMISSION_STATE=" + state.name());
        if ((state == DisplayPolicy.Admission.FAULTED ||
                state == DisplayPolicy.Admission.WINDOW_REJECTED ||
                state == DisplayPolicy.Admission.FAILED) && !closing) {
            releaseRenderer();
            active = false;
            closeIpcSession();
        }
    }

    /** The Presentation/SurfaceView owns this borrowed handle; this app never releases it. */
    public void surface(Surface surface) {
        borrowedPresentationSurface = surface;
        if (surface == null) {
            log("SURFACE_BORROWED_LOST owner=Presentation_SurfaceHolder released_by_app=false");
            if (!closing && active) releaseRenderer();
        } else {
            log("SURFACE_BORROWED_READY valid=" + surface.isValid() +
                    " owner=Presentation_SurfaceHolder released_by_app=false");
        }
    }

    public void error(String operation, String exceptionType) {
        log("ADMISSION_ERROR operation=" + operation + " type=" + exceptionType);
        setStatus("Presentation failed closed: " + exceptionType);
    }

    public void presentationRoot(final FrameLayout root) {
        if (!active || closing || root == null || activeGeneration <= 0) return;
        presentationRoot = root;
        final long generation = activeGeneration;
        Display1OutputBackend.Host contentHost = new Display1OutputBackend.Host() {
            private View ownedContent;
            private long ownedGeneration;
            public FrameLayout getMainLayer() { return active && !closing ? root : null; }
            public boolean isNavigationPageActive() { return active && !closing && presentationRoot == root; }
            public boolean attachContent(View content, long requestedGeneration) {
                if (!isNavigationPageActive() || content == null || requestedGeneration != generation ||
                        content.getParent() != null) return false;
                root.addView(content);
                ownedContent = content;
                ownedGeneration = requestedGeneration;
                return true;
            }
            public boolean detachContent(View content, long requestedGeneration) {
                if (ownedContent != content || ownedGeneration != requestedGeneration) return false;
                root.removeView(content);
                ownedContent = null;
                ownedGeneration = 0L;
                return true;
            }
        };
        try {
            RendererViewport geometry = new RendererViewport(
                    new RendererViewport.Bounds(100, 60, 700, 420),
                    java.util.Collections.singletonList(new RendererViewport.Bounds(300, 170, 500, 270)),
                    RendererViewport.SYNTHETIC_TEST_ONLY);
            renderer = new Display1OutputBackend(contentHost,
                    new Display1OutputBackend.Viewport(0, 0, 800, 480), generation, geometry);
            renderer.attach();
            TextView label = new TextView(root.getContext());
            label.setText("CLARITYLINK\nTEST 6A\nBINDER → VIEW\nLAB ONLY");
            label.setTextSize(14.0f);
            label.setTextColor(Color.WHITE);
            label.setBackgroundColor(0xcc000000);
            FrameLayout.LayoutParams labelParams = new FrameLayout.LayoutParams(
                    FrameLayout.LayoutParams.WRAP_CONTENT, FrameLayout.LayoutParams.WRAP_CONTENT);
            root.addView(label, labelParams);
            if (ipcSessionReady) {
                if (reattachSessionId > 0L && type111FixtureMode)
                    startType111FixtureRun(generation);
                else submitSyntheticFrame(generation);
            }
        } catch (RuntimeException failure) {
            log("RENDERER_ATTACH_FAILED type=" + failure.getClass().getSimpleName());
            releaseRenderer();
            if (displayHost != null) displayHost.close();
            active = false;
        }
    }

    private void awaitFrame(final int attempt, final long generation, final long expectedTimestampNs) {
        main.postDelayed(new Runnable() {
            public void run() {
                if (!active || closing || renderer == null || generation != activeGeneration) return;
                ClarityLinkContentView view = renderer.contentView();
                if (view != null && view.drawnGeneration() == generation &&
                        view.drawnTimestampNs() == expectedTimestampNs) {
                    FrameViewSink.TestControl raceControl = warningRaceControl;
                    if (raceControl != null) raceControl.recoveryDrawn(expectedTimestampNs);
                    if (expectedTimestampNs == 1L && !canvasDrawLogged) {
                        canvasDrawLogged = true;
                        log("BINDER_FRAME_DRAWN_ON_PRESENTATION_VIEW generation=" + generation +
                                " timestamp=1 renderer=ClarityLinkContentView");
                        log("SYNTHETIC_FRAME_DRAWN_ON_PRESENTATION_CANVAS generation=" + generation +
                                " timestamp=1 path=binder_to_view compatibility_marker=true");
                        saveBinderViewProof();
                    }
                    if (expectedTimestampNs == 1L && !rendererScenarioValidated) {
                        verifySyntheticGeometry(view);
                        if (generation <= 1L || view.submitFrame(syntheticFrame(2L), generation - 1L))
                            throw new IllegalStateException("stale_generation_accepted");
                        view.onHostSuspended(HostedContentLifecycle.WARNING_PREEMPTION, generation);
                        if (view.hasDisplayedFrame() || view.submitFrame(syntheticFrame(2L), generation))
                            throw new IllegalStateException("warning_preemption_did_not_clear_or_block");
                        if (hasVisiblePixels(view)) throw new IllegalStateException("warning_pixels_not_cleared");
                        view.onHostResumed(generation);
                        if (!view.submitFrame(syntheticFrame(2L), generation))
                            throw new IllegalStateException("matching_warning_resume_rejected");
                        rendererScenarioValidated = true;
                        log("CLIMP09_RENDER_GEOMETRY_PASS crop=top-row rotation=90 fit=portrait safeAreaAndProtectedMask=synthetic warning=preempt staleGeneration=rejected");
                        awaitFrame(0, generation, 2L);
                        return;
                    }
                    if (expectedTimestampNs == 2L && !warningResumeValidated) {
                        warningResumeValidated = true;
                        log("CLIMP09_WARNING_RESUME_PASS generation=" + generation + " timestamp=2");
                    }
                    if (ipcSessionReady && !ipcSubmitted) submitSyntheticFrame(generation);
                    if (expectedTimestampNs == 2L && warningResumeValidated && !diagnosticRunStarted) {
                        if (type111FixtureMode) startType111FixtureRun(generation);
                        else startDiagnosticRun(generation);
                        return;
                    }
                    if (diagnosticRunStarted && expectedTimestampNs > 2L) {
                        if (expectedTimestampNs <= lastDiagnosticDrawTimestampNs) return;
                        lastDiagnosticDrawTimestampNs = expectedTimestampNs;
                        log("DIAGNOSTIC_FRAME_DRAWN counter=" + diagnosticFrameIndex +
                                " generation=" + generation + " timestamp_ns=" + expectedTimestampNs);
                        saveBinderViewProof("api17-diagnostic-frame-" + diagnosticFrameIndex + ".png");
                        if (diagnosticFrameIndex < 4) {
                            main.postDelayed(new Runnable() { public void run() {
                                submitNextSyntheticDiagnosticFrame(generation);
                            }}, 120L);
                        } else {
                            log("DIAGNOSTIC_FRAME_PIPELINE_PASS static=1 synthetic=3 canvas_frames=4 " +
                                    "source=800x480 lab_only=true honda_backend=disabled");
                            closeDiagnosticSources();
                            if (!warningRaceStarted) startBinderWarningRace(generation);
                        }
                        return;
                    }
                    else if (!ipcSessionReady) awaitFrame(attempt + 1, generation, expectedTimestampNs);
                    return;
                }
                if (view != null && view.drawnGeneration() == generation &&
                        view.drawnTimestampNs() > expectedTimestampNs) {
                    log("VIEW_FRAME_SUPERSEDED generation=" + generation +
                            " expected_timestamp=" + expectedTimestampNs +
                            " visible_timestamp=" + view.drawnTimestampNs() +
                            " stale_wait_abandoned=true");
                    return;
                }
                if (attempt >= 120) {
                    log("SYNTHETIC_FRAME_TIMEOUT timestamp=" + expectedTimestampNs);
                    stopOwnedDisplay("frame-timeout");
                    return;
                }
                awaitFrame(attempt + 1, generation, expectedTimestampNs);
            }
        }, 50L);
    }

    private void startBinderWarningRace(final long generation) {
        if (warningRaceStarted || !active || closing || renderer == null || !ipcSessionReady) return;
        warningRaceStarted = true;
        final FrameViewSink.TestControl control = new FrameViewSink.TestControl();
        warningRaceControl = control;
        viewSink.setDispatchProbe(control);
        final long base = Math.max(System.nanoTime(), lastDiagnosticDrawTimestampNs) + 1_000_000L;
        final long first = base;
        final long second = base + 1L;
        final long third = base + 2L;
        final long midDispatch = base + 3L;
        final long fresh = base + 4L;
        control.recoveryTimestamp = fresh;

        new Thread(new Runnable() {
            public void run() {
                try {
                    control.pauseHandlerAt(first);
                    requireRace(sendRaceFrame(generation, first), "first Binder frame accepted");
                    requireRace(awaitRace(control.handlerEntered), "Handler callback entered barrier");
                    requireRace(sendRaceFrame(generation, second), "second Binder frame accepted");
                    requireRace(sendRaceFrame(generation, third), "third Binder frame accepted");
                    requireRace(viewSink.queuedFrameCount() == FrameViewSink.MAX_QUEUED_FRAMES,
                            "bounded UI queue holds three frames");
                    control.expectWarning(true);
                    requireRace(setRaceWarning(generation, true), "warning Binder transaction accepted");
                    control.releaseHandler.countDown();
                    requireRace(awaitRace(control.warningApplied), "queued warning applied to View");
                    requireNoRaceFrameDrawn(first, second, third);
                    log("CL_R1_CASE_PASS case=warning_before_handler_dispatch queued=3 dropped=3");

                    control.expectWarning(false);
                    requireRace(setRaceWarning(generation, false), "warning clear transaction accepted");
                    requireRace(awaitRace(control.warningCleared), "warning clear applied to View");

                    control.pauseViewAt(midDispatch);
                    requireRace(sendRaceFrame(generation, midDispatch), "mid-dispatch frame accepted");
                    requireRace(awaitRace(control.viewSubmitted), "Handler submitted frame to View");
                    control.expectWarning(true);
                    requireRace(setRaceWarning(generation, true), "mid-dispatch warning accepted");
                    control.releaseView.countDown();
                    requireRace(awaitRace(control.warningApplied), "mid-dispatch warning applied");
                    requireNoRaceFrameDrawn(midDispatch);
                    log("CL_R1_CASE_PASS case=warning_after_view_submit_before_draw suppressed=true");

                    control.expectWarning(false);
                    requireRace(setRaceWarning(generation, false), "mid-dispatch warning clear accepted");
                    requireRace(awaitRace(control.warningCleared), "mid-dispatch warning clear applied");
                    requireRace(sendRaceFrame(generation, fresh), "fresh recovery frame accepted");
                    requireRace(awaitRace(control.recoveryDrawn), "fresh frame visibly drawn after warning");
                    requireRace(!control.barrierTimedOut, "all test barriers released within bound");
                    log("CL_R1_BINDER_HANDLER_VIEW_RACE_PASS queued_frames=3 warning_before_dispatch=pass " +
                            "warning_during_dispatch=pass stale_after_clear=none fresh_recovery=pass " +
                            "transport=separate_process_binder_pfd");
                    String[] malformedCases = new String[] { "negative_dimensions", "zero_dimensions",
                            "oversized_dimensions", "integer_overflow_dimensions",
                            "unsupported_pixel_format", "invalid_stride",
                            "short_payload", "long_payload", "missing_pfd", "invalid_crop",
                            "stale_generation" };
                    FrameIpcClient liveClient = frameIpcClient;
                    requireRace(liveClient != null, "live Binder client available for malformed probes");
                    for (int index = 0; index < malformedCases.length; index++) {
                        String malformed = malformedCases[index];
                        String rejection;
                        try {
                            rejection = liveClient.probeMalformed(malformed, generation,
                                    fresh + index + 1L);
                        } catch (Exception failure) {
                            throw new RuntimeException("malformed_binder_probe_" + malformed +
                                    "_failed_" + failure.getClass().getSimpleName());
                        }
                        log("CL_R3_MALFORMED_BINDER_REJECT case=" + malformed +
                                " reason=" + rejection + " process_responsive=true");
                    }
                    long postMalformed = fresh + malformedCases.length + 1L;
                    control.recoveryTimestamp = postMalformed;
                    control.recoveryDrawn = new CountDownLatch(1);
                    requireRace(sendRaceFrame(generation, postMalformed),
                            "valid frame accepted after malformed Binder requests");
                    requireRace(awaitRace(control.recoveryDrawn),
                            "valid View frame drawn after malformed Binder requests");
                    log("CL_R3_MALFORMED_BINDER_SUITE_PASS cases=" + malformedCases.length +
                            " same_session=true post_rejection_frame_drawn=true");
                    long currentGeneration = generation;
                    int sessionIdentity = liveClient.sessionIdentity();
                    for (int transition = 1; transition <= 2; transition++) {
                        FrameStreamIdentity previousIdentity = liveClient.streamIdentity();
                        long nextGeneration = currentGeneration + 1L;
                        boolean replaced;
                        try { replaced = liveClient.replaceGeneration(currentGeneration, nextGeneration); }
                        catch (android.os.RemoteException failure) {
                            throw new RuntimeException("binder_generation_transition_remote_exception");
                        }
                        requireRace(replaced, "generation transition accepted on existing Binder session");
                        long frameTimestamp = postMalformed + transition * 1000L;
                        control.recoveryTimestamp = frameTimestamp;
                        control.recoveryDrawn = new CountDownLatch(1);
                        requireRace(sendRaceFrame(nextGeneration, frameTimestamp),
                                "new generation frame accepted");
                        requireRace(awaitViewFrameDrawn(activeGeneration, frameTimestamp),
                                "new generation frame drawn");
                        requireRace(liveClient.sessionIdentity() == sessionIdentity,
                                "Binder endpoint identity preserved across generation transition");
                        boolean staleEndAccepted;
                        try { staleEndAccepted = liveClient.probeEndIdentity(previousIdentity); }
                        catch (android.os.RemoteException failure) {
                            throw new RuntimeException("stale_end_probe_remote_exception");
                        }
                        requireRace(!staleEndAccepted,
                                "stale END from prior generation rejected over Binder");
                        long afterStaleEndTimestamp = postMalformed + transition * 1000L + 500L;
                        control.recoveryTimestamp = afterStaleEndTimestamp;
                        control.recoveryDrawn = new CountDownLatch(1);
                        requireRace(sendRaceFrame(nextGeneration, afterStaleEndTimestamp),
                                "current generation remains active after stale Binder END");
                        requireRace(awaitViewFrameDrawn(activeGeneration, afterStaleEndTimestamp),
                                "current generation draws after stale Binder END");
                        log("CL_R3_GENERATION_FRAME_PASS stream_generation=" + nextGeneration +
                                " parent_display_generation=" + activeGeneration + " transition=" +
                                transition + " same_binder_endpoint=true stale_end_rejected=true " +
                                "new_generation_continued=true");
                        currentGeneration = nextGeneration;
                    }
                    String staleReason;
                    try {
                        staleReason = liveClient.probeMalformed("stale_generation", currentGeneration,
                                postMalformed + 3000L);
                    } catch (Exception failure) {
                        throw new RuntimeException("stale_generation_after_transition_failed");
                    }
                    requireRace("frame_contract_rejected".equals(staleReason),
                            "old generation rejected after live transition");
                    control.expectWarning(true);
                    requireRace(setRaceWarning(currentGeneration, true),
                            "warning before stale-generation replay accepted");
                    requireRace(awaitRace(control.warningApplied), "warning preemption applied after transition");
                    control.expectWarning(false);
                    requireRace(setRaceWarning(currentGeneration, false), "warning clearance after transition");
                    requireRace(awaitRace(control.warningCleared), "warning cleared after transition");
                    long resumedTimestamp = postMalformed + 4000L;
                    control.recoveryTimestamp = resumedTimestamp;
                    control.recoveryDrawn = new CountDownLatch(1);
                    requireRace(sendRaceFrame(currentGeneration, resumedTimestamp),
                            "fresh current-generation frame accepted after warning");
                    requireRace(awaitViewFrameDrawn(activeGeneration, resumedTimestamp),
                            "fresh current-generation frame drawn after warning");
                    log("CL_R3_GENERATION_TRANSITION_PASS transitions=2 rapid=true " +
                            "stale_generation_rejected=" + staleReason +
                            " binder_endpoint=" + sessionIdentity + " view_instance_preserved=true");
                    viewSink.setDispatchProbe(null);
                    warningRaceControl = null;
                    if (crashAfterFirstFrame) {
                        crashAfterFirstFrame = false;
                        FrameStreamIdentity primaryIdentity = primaryLabIpcClient == null ? null :
                                primaryLabIpcClient.streamIdentity();
                        FrameLabSink.Stats primaryStats = queryType110StatsOrThrow(
                                "uncaught_crash_type110_receipt_unavailable");
                        if (primaryIdentity == null)
                            throw new IllegalStateException("uncaught_crash_type110_receipt_unavailable");
                        issueType110ProbeOwnership(primaryIdentity, primaryStats);
                        log("CL_R2_UNCAUGHT_CRASH_REQUESTED pid=" + android.os.Process.myPid() +
                                " session_id=" + primaryIdentity.sessionId +
                                " type110_connection_id=" + primaryIdentity.connectionId +
                                " type110_generation=" + primaryIdentity.streamGeneration +
                                " type110_last_frame_id=" + primaryStats.frameId +
                                " type110_sink_pid=" + primaryStats.pid +
                                " compositor_pid=" + compositorRemotePid);
                        main.post(new Runnable() {
                            public void run() {
                                throw new RuntimeException(
                                        "CL-IMP-03 emulator-only crash recovery probe");
                            }
                        });
                    }
                    if (controlledExitAfterValidation) {
                        FrameStreamIdentity primaryIdentity = primaryLabIpcClient == null ? null :
                                primaryLabIpcClient.streamIdentity();
                        FrameLabSink.Stats primaryStats = queryType110StatsOrThrow(
                                "controlled_exit_type110_receipt_unavailable");
                        if (primaryIdentity == null)
                            throw new IllegalStateException("controlled_exit_type110_receipt_unavailable");
                        issueType110ProbeOwnership(primaryIdentity, primaryStats);
                        log("CL_R2_CONTROLLED_PROCESS_EXIT_REQUESTED pid=" + android.os.Process.myPid() +
                                " session_id=" + primaryIdentity.sessionId +
                                " type110_connection_id=" + primaryIdentity.connectionId +
                                " type110_generation=" + primaryIdentity.streamGeneration +
                                " type110_last_frame_id=" + primaryStats.frameId +
                                " type110_sink_pid=" + primaryStats.pid +
                                " compositor_pid=" + compositorRemotePid);
                        android.os.Process.killProcess(android.os.Process.myPid());
                    }
                } catch (RuntimeException failure) {
                    control.releaseHandler.countDown();
                    control.releaseView.countDown();
                    viewSink.setDispatchProbe(null);
                    warningRaceControl = null;
                    log("CL_R1_BINDER_HANDLER_VIEW_RACE_FAIL reason=" + failure.getMessage());
                    stopOwnedDisplay("warning-race-test-failed");
                }
            }
        }, "ClarityLinkWarningRaceProbe").start();
    }

    private boolean sendRaceFrame(final long generation, final long timestampNs) {
        final CountDownLatch completed = new CountDownLatch(1);
        final boolean[] accepted = new boolean[] { false };
        FrameIpcClient client = frameIpcClient;
        if (client == null || !client.submit(syntheticFrame(timestampNs), generation,
                new FrameIpcClient.Callback() {
                    public void complete(boolean result, String reason) {
                        accepted[0] = result;
                        if (!result) log("CL_R1_FRAME_REJECTED timestamp=" + timestampNs + " reason=" + reason);
                        completed.countDown();
                    }
                })) return false;
        return awaitRace(completed) && accepted[0];
    }

    private boolean setRaceWarning(long generation, boolean visible) {
        FrameIpcClient client = frameIpcClient;
        if (client == null) return false;
        try { return client.setWarningVisible(generation, visible); }
        catch (android.os.RemoteException failure) { return false; }
    }

    private void requireNoRaceFrameDrawn(long... timestamps) {
        ClarityLinkContentView view = renderer == null ? null : renderer.contentView();
        requireRace(view != null && !view.hasDisplayedFrame(), "warning clears View content");
        long drawn = view.drawnTimestampNs();
        for (long timestamp : timestamps)
            requireRace(drawn != timestamp, "stale frame timestamp was not drawn");
    }

    private static boolean awaitRace(CountDownLatch latch) {
        try { return latch.await(10L, TimeUnit.SECONDS); }
        catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            return false;
        }
    }

    /** Waits for the View's onDraw receipt, rather than transaction acceptance or enqueue. */
    private boolean awaitViewFrameDrawn(long expectedGeneration, long expectedTimestampNs) {
        long deadline = SystemClock.uptimeMillis() + 10000L;
        while (SystemClock.uptimeMillis() < deadline) {
            Display1OutputBackend currentRenderer = renderer;
            ClarityLinkContentView currentView = currentRenderer == null ? null : currentRenderer.contentView();
            if (currentView != null && currentView.drawnGeneration() == expectedGeneration &&
                    currentView.drawnTimestampNs() == expectedTimestampNs) return true;
            try { Thread.sleep(20L); }
            catch (InterruptedException interrupted) {
                Thread.currentThread().interrupt();
                return false;
            }
        }
        ClarityLinkContentView currentView = renderer == null ? null : renderer.contentView();
        // The draw receipt can arrive between the final sleep and the deadline check.
        // Re-read once at the boundary so a frame actually drawn by the deadline is not
        // reported as a timeout merely because the polling loop crossed that boundary.
        if (currentView != null && currentView.drawnGeneration() == expectedGeneration &&
                currentView.drawnTimestampNs() == expectedTimestampNs) return true;
        log("CL_R3_VIEW_DRAW_TIMEOUT expected_generation=" + expectedGeneration +
                " expected_timestamp=" + expectedTimestampNs + " displayed_generation=" +
                (currentView == null ? -1 : currentView.displayedGeneration()) +
                " displayed_timestamp=" + (currentView == null ? -1 : currentView.displayedTimestampNs()) +
                " drawn_generation=" + (currentView == null ? -1 : currentView.drawnGeneration()) +
                " drawn_timestamp=" + (currentView == null ? -1 : currentView.drawnTimestampNs()));
        return false;
    }

    private static void requireRace(boolean result, String description) {
        if (!result) throw new RuntimeException("warning_race_" + description.replace(' ', '_'));
    }

    private void awaitRaceRecoveryFrame(final int attempt, final long generation, final long timestampNs) {
        main.postDelayed(new Runnable() {
            public void run() {
                if (!active || closing || renderer == null || generation != activeGeneration) return;
                ClarityLinkContentView view = renderer.contentView();
                if (view != null && view.drawnGeneration() == generation &&
                        view.drawnTimestampNs() == timestampNs) {
                    FrameViewSink.TestControl control = warningRaceControl;
                    if (control != null) control.recoveryDrawn(timestampNs);
                    return;
                }
                if (attempt >= 120) {
                    log("CL_R1_RECOVERY_FRAME_TIMEOUT timestamp=" + timestampNs);
                    return;
                }
                awaitRaceRecoveryFrame(attempt + 1, generation, timestampNs);
            }
        }, 50L);
    }

    private void startDiagnosticRun(final long generation) {
        if (diagnosticRunStarted || !active || renderer == null || generation != activeGeneration) return;
        diagnosticRunStarted = true;
        staticDiagnosticSource = new DiagnosticFrameSource(800, 480,
                DiagnosticFrameSource.Mode.STATIC);
        syntheticDiagnosticSource = new DiagnosticFrameSource(800, 480,
                DiagnosticFrameSource.Mode.SYNTHETIC_VIDEO);
        FrameSource source = staticDiagnosticSource;
        DecodedFrame frame = source.nextFrame(generation);
        if (frame == null) {
            stopOwnedDisplay("diagnostic-static-frame-unavailable");
            return;
        }
        submitDiagnosticFrame(frame, generation);
    }

    /** CL-R4 lab-only fixture path: parser -> API17 YUV buffers -> RGBA -> Binder/PFD -> View. */
    private void startType111FixtureRun(final long binderGeneration) {
        if (!active || closing || renderer == null || frameIpcClient == null) return;
        Thread previousWorker = type111FixtureWorker;
        if (previousWorker != null && previousWorker.isAlive()) {
            main.postDelayed(new Runnable() {
                public void run() { startType111FixtureRun(binderGeneration); }
            }, 100L);
            return;
        }
        if (type111RunStarted) return;
        type111RunStarted = true;
        final FixtureRunToken runToken = new FixtureRunToken();
        type111FixtureRunToken = runToken;
        fixtureTimestampOffsetNs = reattachSessionId > 0L ? 1000000000000L : 0L;
        lastType111SubmissionTimestampNs = fixtureTimestampOffsetNs;
        type111FixtureWorker = new Thread(new Runnable() {
            public void run() {
                Api17BufferH264Decoder decoder = null;
                Api17BufferH264Decoder type110Decoder = null;
                try {
                    byte[] blueFixture = type111Fixture("type111-blue-32x32.h264.b64");
                    byte[] blueConfig = Api17SurfaceH264Decoder.extractCodecConfig(blueFixture);
                    byte[][] blueAccessUnits = Api17SurfaceH264Decoder.extractVclFrames(blueFixture);
                    requireType111(blueAccessUnits.length >= 2 &&
                            (blueAccessUnits[0][4] & 31) == 5, "blue_fixture_starts_with_idr_and_has_frames");
                    Type111ControlClient control = type111ControlClient;
                    FrameStreamIdentity controlIdentity = frameIpcClient.streamIdentity();
                    requireType111(control != null && control.navigation(controlIdentity,
                            "maps", true, true), "type111_navigation_eligible");
                    requireType111(control.presentation(controlIdentity, "suggestUI",
                            Type111ControlPlane.MAP_CONTEXT), "type111_map_ui_suggested");
                    requireType111(control.geometry(controlIdentity, new int[] { 0, 0, 800, 480 }, false),
                            "type111_view_area_accepted");
                    requireType111(control.geometry(controlIdentity, new int[] { 16, 16, 784, 464 }, true),
                            "type111_safe_area_accepted");
                    requireType111(control.presentation(controlIdentity, "showUI", null),
                            "type111_map_ui_selected");
                    requireType111(!control.navigation(controlIdentity, "unknown", true, false),
                            "unsupported_navigation_provider_rejected");
                    requireType111(!control.presentation(controlIdentity, "suggestUI", "unsupported:context"),
                            "unsupported_ui_context_rejected");
                    requireType111(!control.geometry(controlIdentity, new int[] { 0, 0, 801, 480 }, false),
                            "out_of_bounds_view_area_rejected");
                    Log.i(TAG, "CL_R5_API17_CONTROL_VALIDATION_PASS duplicate_capability=true " +
                            "duplicate_setup=true unsupported_provider=true unsupported_context=true " +
                            "out_of_bounds_geometry=true");
                    requireType111(control.videoConfig(controlIdentity, 32, 32) > 0,
                            "type111_initial_video_config");
                    decoder = new Api17BufferH264Decoder(32, 32, 960001L, blueConfig);
                    byte[] type110Fixture = type111Fixture("type110-red-32x32.h264.b64");
                    byte[] type110Config = Api17SurfaceH264Decoder.extractCodecConfig(type110Fixture);
                    byte[][] type110AccessUnits = Api17SurfaceH264Decoder.extractVclFrames(type110Fixture);
                    requireType111(type110AccessUnits.length >= 2 &&
                            (type110AccessUnits[0][4] & 31) == 5, "type110_fixture_starts_with_idr");
                    type110Decoder = new Api17BufferH264Decoder(32, 32, 970001L, type110Config);
                    Log.i(TAG, "CL_R4_DUAL_FIXTURE_DECODERS_STARTED type111_generation=960001 " +
                            "type110_generation=970001 independent_codec_instances=true");
                    int blueColorFormat = -1;
                    long lastOutputPts = -1L;
                    int blueOutputs = 0;
                    int sentFrames = 0;
                    boolean backpressureVerified = false;
                    long inputPts = fixturePtsUs(100000L);
                    for (int index = 0; index < 8 && blueOutputs < 4; index++, inputPts += 100000L) {
                        byte[] accessUnit = blueAccessUnits[index % blueAccessUnits.length];
                        DecodedFrame frame = decoder.decode(accessUnit, inputPts, 960001L, 3000L);
                        if (frame == null) continue;
                        requireType111(frame.width == 32 && frame.height == 32,
                                "blue_decoder_output_dimensions");
                        requireType111(frame.presentationTimeNs > lastOutputPts,
                                "blue_decoded_frame_order");
                        int[] blueRgb = readDecodedCenterRgb(frame);
                        requireType111(blueRgb[2] > blueRgb[0], "blue_fixture_decoded_pixel_content");
                        blueColorFormat = decoder.colorFormat();
                        submitDecodedFrame(frame, binderGeneration, !backpressureVerified);
                        backpressureVerified = true;
                        lastOutputPts = frame.presentationTimeNs;
                        blueOutputs++;
                        sentFrames++;
                        if (blueOutputs == 1 || blueOutputs == 4)
                            captureType111Proof("type111-blue-frame-" + blueOutputs + ".png");
                    }
                    requireType111(blueOutputs >= 2, "multiple_blue_video_frames_decoded_and_drawn");
                    if (getIntent() != null && getIntent().getBooleanExtra(
                            EXTRA_SECURITY_LIVE_PRODUCER, false)) {
                        bindSecurityTestProducerService();
                    }
                    startSameUidRegistrationAttack(primaryLabIpcClient.streamIdentity(),
                            frameIpcClient.streamIdentity());
                    if (getIntent() != null && getIntent().getBooleanExtra(
                            "hold_after_same_uid_attack", false)) {
                        awaitCrossUidRunnerRelease(primaryLabIpcClient.streamIdentity().sessionId);
                    }
                    String decoderFault;
                    try {
                        injectType111DecoderFaultForLab();
                        throw new IllegalStateException("decoder_fault_hook_did_not_fire");
                    } catch (Api17SurfaceH264Decoder.DecodeException expected) {
                        decoderFault = expected.getMessage();
                    }
                    requireType111("lab_injected_type111_decoder_failure".equals(decoderFault),
                            "controlled_type111_decoder_failure_classified");
                    decoder.close();
                    decoder = null;
                    control.videoConfig(controlIdentity, 32, 32);
                    decoder = new Api17BufferH264Decoder(32, 32, 960002L, blueConfig);
                    DecodedFrame afterDecoderFault = decodeFixtureFrame(decoder, blueAccessUnits,
                            960002L, Math.max(inputPts, 600000L), 600000000L);
                    int[] recoveredRgb = readDecodedCenterRgb(afterDecoderFault);
                    requireType111(recoveredRgb[2] > recoveredRgb[0],
                            "type111_video_recovers_after_decoder_fault");
                    submitDecodedFrame(afterDecoderFault, binderGeneration, false);
                    requireType111(primaryLabIpcClient.streamIdentity() != null &&
                            primaryLabIpcClient.streamIdentity().streamType == FrameStreamIdentity.TYPE110,
                            "type110_identity_survives_type111_decoder_failure");
                    Log.i(TAG, "CL_R4_TYPE111_DECODER_FAULT_RECOVERY_PASS failure=" + decoderFault +
                            " codec_closed=true codec_recreated=true new_decoder_generation=960002 " +
                            "type111_frame_redrawn=true type110_identity_preserved=true " +
                            "parent_and_transport_preserved=true injected_test_hook=true");
                    DecodedFrame type110BeforeReset = decodeFixtureFrame(type110Decoder,
                            type110AccessUnits, 970001L, 500000L, 400000000L);
                    int[] type110FirstRgb = readDecodedCenterRgb(type110BeforeReset);
                    requireType111(type110FirstRgb[0] > type110FirstRgb[1] &&
                            type110FirstRgb[0] > type110FirstRgb[2], "type110_fixture_red_content_before_type111_reset");
                    submitType110DecodedFrame(type110BeforeReset, binderGeneration);
                    Log.i(TAG, "CL_R4_TYPE110_FIXTURE_FRAME_PASS timing=before_type111_reset " +
                            "decoder_generation=970001 binder_generation=" + binderGeneration);

                    byte[] greenFixture = type111Fixture("type111-green-64x64.h264.b64");
                    byte[] greenConfig = Api17SurfaceH264Decoder.extractCodecConfig(greenFixture);
                    byte[][] greenAccessUnits = Api17SurfaceH264Decoder.extractVclFrames(greenFixture);
                    requireType111(greenAccessUnits.length >= 2 &&
                            (greenAccessUnits[0][4] & 31) == 5,
                            "green_fixture_restarts_from_idr_keyframe");
                    decoder.reset(64, 64, 960003L, greenConfig);
                    long decoderGeneration = control.videoConfig(controlIdentity, 64, 64);
                    requireType111(decoderGeneration > 1L, "type111_decoder_generation_advanced");
                    requireType111(control.navigation(controlIdentity, "waze", true, false),
                            "provider_change_preserves_type111_stream");
                    requireType111(controlIdentity.equals(frameIpcClient.streamIdentity()),
                            "provider_change_preserved_transport_identity");
                    requireType111(control.presentation(controlIdentity, "stopUI", null),
                            "type111_presentation_hidden");
                    requireType111(control.presentation(controlIdentity, "suggestUI",
                            Type111ControlPlane.MAP_CONTEXT), "type111_ui_resuggested_after_provider_change");
                    requireType111(control.presentation(controlIdentity, "showUI", null),
                            "type111_ui_restored_without_transport_restart");
                    Log.i(TAG, "CL_R5_API17_PRESENTATION_LIFETIME_PASS maps_to_waze=true " +
                            "hide_show=true transport_identity_preserved=true " +
                            "decoder_generation=" + decoderGeneration);
                    Log.i(TAG, "CL_R4_DECODER_RESTART old_size=32x32 new_size=64x64 " +
                            "decoder_generation=960003 binder_generation=" + binderGeneration);
                    long greenLastPts = lastOutputPts;
                    int greenColorFormat = -1;
                    int greenOutputs = 0;
                    DecodedFrame latestGreenFrame = null;
                    inputPts = fixturePtsUs(900000L);
                    for (int index = 0; index < 8 && greenOutputs < 3; index++, inputPts += 100000L) {
                        DecodedFrame frame = decoder.decode(
                                greenAccessUnits[index % greenAccessUnits.length], inputPts, 960003L, 3000L);
                        if (frame == null) continue;
                        requireType111(frame.width == 64 && frame.height == 64,
                                "green_decoder_resolution_change");
                        requireType111(frame.presentationTimeNs > greenLastPts,
                                "green_decoded_frame_order");
                        int[] rgb = readDecodedCenterRgb(frame);
                        requireType111(rgb[1] > rgb[0], "green_fixture_decoded_pixel_content");
                        greenColorFormat = decoder.colorFormat();
                        submitDecodedFrame(frame, binderGeneration, false);
                        latestGreenFrame = frame;
                        greenLastPts = frame.presentationTimeNs;
                        greenOutputs++;
                        sentFrames++;
                        if (greenOutputs == 1 || greenOutputs == 3)
                            captureType111Proof("type111-green-frame-" + greenOutputs + ".png");
                    }
                    requireType111(greenOutputs >= 2, "multiple_green_video_frames_decoded_and_drawn");
                    requireType111(backpressureVerified, "bounded_queue_backpressure_verified");
                    DecodedFrame type110AfterReset = decodeFixtureFrame(type110Decoder,
                            type110AccessUnits, 970001L, 1200000L, 1100000000L);
                    int[] type110SecondRgb = readDecodedCenterRgb(type110AfterReset);
                    requireType111(type110SecondRgb[0] > type110SecondRgb[1] &&
                            type110SecondRgb[0] > type110SecondRgb[2], "type110_fixture_red_content_after_type111_reset");
                    submitType110DecodedFrame(type110AfterReset, binderGeneration);
                    Log.i(TAG, "CL_R4_TYPE110_ISOLATION_PASS type111_decoder_reset=true " +
                            "type110_decoder_generation=970001 type110_frame_before_after=true " +
                            "binder_session_preserved=true fixture_only=true");
                    DecodedFrame paddedCrop = paddedCropFixtureFrame(fixtureTimestamp(4000000000L));
                    int[] croppedRgb = readDecodedCenterRgb(paddedCrop);
                    requireType111(paddedCrop.rowStride == 128 && paddedCrop.cropLeft == 8 &&
                            paddedCrop.cropTop == 8 && paddedCrop.cropRight == 24 &&
                            paddedCrop.cropBottom == 24 && croppedRgb[0] > 220 && croppedRgb[1] < 40,
                            "padded_stride_nonzero_crop_adapter_content");
                    submitDecodedFrame(paddedCrop, binderGeneration, false);
                    captureType111Proof("type111-padded-crop-frame.png");
                    Log.i(TAG, "CL_R4_PADDED_CROP_VIEW_PASS adapter=YUV420-planar source_stride=40 " +
                            "source_slice_height=40 crop=8,8,24,24 binder_pfd=true view_draw=true " +
                            "decoded_h264_output=false");
                    DecodedFrame type110DuringStall = decodeFixtureFrame(type110Decoder,
                            type110AccessUnits, 970001L, 1400000L, 1300000000L);
                    runApi17DualStreamSaturation(latestGreenFrame, type110DuringStall, binderGeneration);
                    FrameStreamIdentity oldType111 = frameIpcClient.streamIdentity();
                    long nextType111Generation = oldType111.streamGeneration + 1L;
                    requireType111(frameIpcClient.replaceGeneration(oldType111.streamGeneration,
                            nextType111Generation), "type111_transport_generation_changed_in_live_session");
                    requireType111(frameIpcClient.streamIdentity().sessionId == oldType111.sessionId &&
                            frameIpcClient.streamIdentity().connectionId == oldType111.connectionId,
                            "type111_transport_session_and_connection_preserved");
                    requireType111(control.videoConfig(frameIpcClient.streamIdentity(), 64, 64) > 1L,
                            "type111_decoder_config_rebound_after_transport_generation");
                    String staleType111 = frameIpcClient.probeMalformed("stale_generation",
                            nextType111Generation, 6000000001L);
                    requireType111("frame_contract_rejected".equals(staleType111),
                            "type111_previous_transport_generation_rejected_by_binder");
                    DecodedFrame recoveredType111 = decodeFixtureFrame(decoder, greenAccessUnits,
                            960003L, 1600000L, 1500000000L);
                    submitDecodedFrame(recoveredType111, binderGeneration, false);
                    Log.i(TAG, "CL_R4_TYPE111_LIVE_GENERATION_PASS old=" + oldType111.streamGeneration +
                            " new=" + nextType111Generation + " connection_preserved=true " +
                            "binder_session_preserved=true stale_rejected=true frame_redrawn=true " +
                            "parent_display_generation=" + binderGeneration);
                    if (reattachSessionId <= 0L) {
                        runIndependentType111ProducerFault(type110Decoder, type110AccessUnits,
                                binderGeneration);
                    } else {
                        Log.i(TAG, "CL_R4A_REATTACH_FIXTURE_PASS producer_process_fault_test=" +
                                "covered_before_view_death=true timestamp_bounds_preserved=true");
                    }
                    decoder.close();
                    decoder = null;
                    type110Decoder.close();
                    type110Decoder = null;
                    requireType111(!frameIpcClient.hasFrameInFlight(), "all_frame_pipe_ownership_released");
                    Log.i(TAG, "CL_R4_TYPE111_BUFFER_DECODE_BINDER_VIEW_PASS blue_frames=" + blueOutputs +
                            " green_frames=" + greenOutputs + " sent_frames=" + sentFrames +
                            " color_format_blue=" + blueColorFormat + " color_format_green=" + greenColorFormat +
                            " backpressure=pass decoder_restart=pass buffer_copy_before_release=true " +
                            "binder_generation=" + binderGeneration + " type110_independent=true " +
                            "authentication=lab_fixture_only");
                    FrameStreamIdentity type110Identity = primaryLabIpcClient.streamIdentity();
                    FrameLabSink.Stats type110Final = FrameLabSink.queryStats(primaryLabSinkBinder);
                    if (type110Identity == null || type110Final == null)
                        throw new IllegalStateException("type110_survivor_receipt_unavailable");
                    if (delayedDeathCallbackTest && reattachSessionId <= 0L &&
                            !type111ControlClient.armLabDelayedSinkDeathCallback(frameIpcClient.streamIdentity()))
                        throw new IllegalStateException("delayed_old_sink_callback_not_armed");
                    if (!type111ReattachTest && !ownerDeathTest)
                        issueType110ProbeOwnership(type110Identity, type110Final);
                    Log.i(TAG, "CL_R4_TYPE111_SINK_PROCESS_EXIT_REQUESTED pid=" +
                            android.os.Process.myPid() + " session_id=" + type110Identity.sessionId +
                            " type110_connection_id=" + type110Identity.connectionId +
                            " type110_generation=" + type110Identity.streamGeneration +
                            " type110_last_frame_id=" + type110Final.frameId +
                            " type110_sink_pid=" + type110Final.pid +
                            " type111_sink_pid=" + android.os.Process.myPid());
                    if (ownerDeathTest) {
                        Log.i(TAG, "CL_R4B_OWNER_SESSION_READY session_id=" + type110Identity.sessionId +
                                " type110_connection_id=" + type110Identity.connectionId +
                                " type110_generation=" + type110Identity.streamGeneration +
                                " type110_last_frame_id=" + type110Final.frameId +
                                " type111_connection_id=" + frameIpcClient.streamIdentity().connectionId +
                                " type111_generation=" + frameIpcClient.streamIdentity().streamGeneration +
                                " parent_owner_pid=" + compositorRemotePid +
                                " valid_type110_and_type111_frames=true session_kept_open=true");
                        return;
                    }
                    if (reentrantTeardownTest) {
                        runReentrantParentTeardown(type110Identity, frameIpcClient.streamIdentity());
                        main.post(new Runnable() {
                            public void run() {
                                stopOwnedDisplay("reentrant-parent-teardown-test-complete");
                            }
                        });
                        return;
                    }
                    if (runToken.isCancelled() || !active || closing) {
                        log("CL_R4A_FIXTURE_CANCELLED_BY_VIEW_LIFECYCLE parent_session_preserved=true");
                        return;
                    }
                    if (reattachSessionId > 0L) {
                        captureType111Proof("type111-reattached-frame.png");
                        FrameLabSink.Stats reattachedType110Stats = queryType110StatsOrThrow(
                                "reattach_type110_stats_unavailable");
                        Type111ControlClient reattachControl = type111ControlClient;
                        if (!runToken.claimTeardown()) {
                            log("CL_R4A_FIXTURE_CANCELLED_BEFORE_PARENT_TEARDOWN parent_session_preserved=true");
                            return;
                        }
                        if (reattachControl == null || !reattachControl.parentTeardown(type110Identity))
                            throw new IllegalStateException("reattached_parent_teardown_rejected");
                        if (delayedDeathCallbackTest) {
                            requireType111(!reattachControl.fireLabDelayedSinkDeathCallback(
                                    type110Identity, frameIpcClient.streamIdentity()),
                                    "callback_release_after_parent_teardown_rejected");
                            Log.i(TAG, "CL_R4B_DELAYED_CALLBACK_POST_TEARDOWN_PASS " +
                                    "stale_release_rejected=true session_not_resurrected=true");
                        }
                        Log.i(TAG, "CL_R4A_VIEW_REATTACH_PASS session_id=" + type110Identity.sessionId +
                                " type110_generation=" + reattachType110Generation +
                                " type110_generation_after_fixture=" + type110Identity.streamGeneration +
                                " type111_generation=" + frameIpcClient.streamIdentity().streamGeneration +
                                " type110_last_frame_id=" + reattachedType110Stats.frameId +
                                " stale_frame_rejected=true parent_teardown=accepted");
                        stopOwnedDisplay("reattach-test-complete");
                    } else {
                        android.os.Process.killProcess(android.os.Process.myPid());
                    }
                } catch (ExpectedType110SinkLoss expectedLoss) {
                    reentrantTeardownInProgress = false;
                    Log.i(TAG, "CL_R4B_TYPE110_EXPECTED_SINK_LOSS session_id=" +
                            expectedLoss.sessionId + " action=close_parent_session");
                    closeType111Lab("type110-lab-sink-disconnected");
                } catch (Throwable failure) {
                    reentrantTeardownInProgress = false;
                    Log.e(TAG, "CL_R4_TYPE111_BUFFER_DECODE_BINDER_VIEW_FAIL", failure);
                    if (!runToken.isCancelled())
                        closeType111Lab("type111_fixture_failed");
                    else log("CL_R4A_FIXTURE_FAILURE_IGNORED_AFTER_VIEW_DETACH parent_session_preserved=true");
                } finally {
                    if (decoder != null) decoder.close();
                    if (type110Decoder != null) type110Decoder.close();
                    if (type111FixtureWorker == Thread.currentThread()) type111FixtureWorker = null;
                }
            }
        }, "ClarityLinkType111FixtureToView");
        type111FixtureWorker.start();
    }

    private void startSameUidRegistrationAttack(FrameStreamIdentity ownerIdentity,
            FrameStreamIdentity childIdentity) {
        if (ownerIdentity == null || childIdentity == null || !ownerIdentity.isValid() ||
                !childIdentity.isValid()) throw new IllegalStateException("same_uid_attack_identity_missing");
        Intent attack = new Intent(this, SameUidRegistrationAttackTestService.class);
        attack.putExtra("session_id", ownerIdentity.sessionId);
        attack.putExtra("owner_connection", ownerIdentity.connectionId);
        attack.putExtra("owner_generation", ownerIdentity.streamGeneration);
        attack.putExtra("child_connection", childIdentity.connectionId);
        attack.putExtra("child_generation", childIdentity.streamGeneration);
        attack.putExtra("hold_after_attack", getIntent() != null &&
                getIntent().getBooleanExtra("hold_after_same_uid_attack", false));
        ComponentName started = startService(attack);
        if (started == null) throw new IllegalStateException("same_uid_attack_service_start_failed");
        Log.i(TAG, "CL_R4B_SAME_UID_ATTACK_STARTED session_id=" + ownerIdentity.sessionId +
                " attacker_process=:registration_attacker");
    }

    /** Bounded API17 harness barrier; the fixture worker holds no receiver or stream lock here. */
    private void awaitCrossUidRunnerRelease(long sessionId) throws InterruptedException {
        java.io.File release = new java.io.File(getFilesDir(),
                "cl-r4b-cross-uid-release-" + sessionId);
        long deadline = android.os.SystemClock.elapsedRealtime() + 120000L;
        Log.i(TAG, "CL_R4B_CROSS_UID_GATE_WAIT session_id=" + sessionId +
                " timeout_ms=120000 test_only=true");
        while (!release.exists() && android.os.SystemClock.elapsedRealtime() < deadline) {
            Thread.sleep(25L);
        }
        if (!release.exists())
            throw new IllegalStateException("cross_uid_runner_gate_timeout_or_release_missing");
        Log.i(TAG, "CL_R4B_CROSS_UID_GATE_RELEASED session_id=" + sessionId +
                " test_only=true");
        releaseSecurityTestProducerService(sessionId);
    }

    /** Holds the real isolated producer service live so API17 can attack its active lifecycle. */
    private void bindSecurityTestProducerService() throws Exception {
        final CountDownLatch connected = new CountDownLatch(1);
        securityProducerConnection = new ServiceConnection() {
            public void onServiceConnected(ComponentName name, IBinder service) {
                int producerPid = -1;
                Parcel data = Parcel.obtain();
                Parcel reply = Parcel.obtain();
                try {
                    data.writeInterfaceToken("org.claritylink.android.IType111LabProducer");
                    if (service.transact(IBinder.FIRST_CALL_TRANSACTION + 2, data, reply, 0)) {
                        reply.readException();
                        producerPid = reply.readInt();
                    }
                } catch (RemoteException | RuntimeException failure) {
                    Log.e(TAG, "TYPE111_SECURITY_TEST_PRODUCER_PID_QUERY_FAILED type=" +
                            failure.getClass().getSimpleName());
                } finally { reply.recycle(); data.recycle(); }
                Log.i(TAG, "TYPE111_SECURITY_TEST_PRODUCER_BOUND view_pid=" +
                        android.os.Process.myPid() + " producer_pid=" +
                        producerPid + " service_process=:type111_producer");
                connected.countDown();
            }
            public void onServiceDisconnected(ComponentName name) {
                Log.i(TAG, "TYPE111_SECURITY_TEST_PRODUCER_DISCONNECTED");
            }
        };
        if (!bindService(new Intent(this, Type111ProducerService.class),
                securityProducerConnection, Context.BIND_AUTO_CREATE))
            throw new IllegalStateException("security_test_producer_bind_rejected");
        securityProducerBound = true;
        if (!connected.await(5L, TimeUnit.SECONDS))
            throw new IllegalStateException("security_test_producer_bind_timeout");
    }

    private synchronized void releaseSecurityTestProducerService(long sessionId) {
        if (!securityProducerBound || securityProducerConnection == null) return;
        try { unbindService(securityProducerConnection); }
        catch (IllegalArgumentException ignored) { }
        securityProducerBound = false;
        securityProducerConnection = null;
        Log.i(TAG, "TYPE111_SECURITY_TEST_PRODUCER_UNBOUND session_id=" + sessionId);
    }

    /** Exercise actual Binder parent teardown concurrently, then verify repeat-close is inert. */
    private void runReentrantParentTeardown(final FrameStreamIdentity owner,
            final FrameStreamIdentity child) throws Exception {
        reentrantTeardownInProgress = true;
        if (owner == null || child == null || owner.streamType != FrameStreamIdentity.TYPE110 ||
                child.streamType != FrameStreamIdentity.TYPE111 || owner.sessionId != child.sessionId)
            throw new IllegalStateException("reentrant_teardown_identity_mismatch");
        final CountDownLatch ready = new CountDownLatch(2);
        final CountDownLatch start = new CountDownLatch(1);
        final CountDownLatch done = new CountDownLatch(2);
        final boolean[] results = new boolean[] { false, false };
        final Throwable[] failures = new Throwable[2];
        final Type111ControlClient control = new Type111ControlClient(compositorEndpoint);
        final CountDownLatch transferDone = new CountDownLatch(1);
        final boolean[] transferAccepted = new boolean[] { true };
        final String[] transferReason = new String[] { "callback_missing" };
        final DecodedFrame pendingFrame = new DecodedFrame(2, 2, 8,
                fixtureTimestamp(9000000000L), 0, 0, 0, 2, 2,
                ByteBuffer.wrap(new byte[] {
                    (byte) 0xff, 0, 0, (byte) 0xff,
                    (byte) 0xff, 0, 0, (byte) 0xff,
                    (byte) 0xff, 0, 0, (byte) 0xff,
                    (byte) 0xff, 0, 0, (byte) 0xff
                }));
        if (frameIpcClient == null ||
                !controlBarrier(FrameIpcProtocol.LAB_ARM_TRANSFER_BARRIER, child, 0L) ||
                !frameIpcClient.submit(pendingFrame, child.streamGeneration,
                new FrameIpcClient.Callback() {
                    public void complete(boolean accepted, String reason) {
                        transferAccepted[0] = accepted;
                        transferReason[0] = reason;
                        transferDone.countDown();
                    }
                }) || !controlBarrier(FrameIpcProtocol.LAB_WAIT_TRANSFER_BARRIER, child, 5000L))
            throw new IllegalStateException("pending_teardown_pfd_barrier_not_reached");
        Log.i(TAG, "CL_R4B_TEARDOWN_PENDING_PFD_PASS session_id=" + owner.sessionId +
                " stream_generation=" + child.streamGeneration + " transfer_active=true");
        if (!control.armLabParentTeardownBarrier(owner))
            throw new IllegalStateException("parent_teardown_overlap_barrier_not_armed");
        for (int index = 0; index < 2; index++) {
            final int slot = index;
            new Thread(new Runnable() {
                public void run() {
                    ready.countDown();
                    try {
                        if (!start.await(5L, TimeUnit.SECONDS))
                            throw new IllegalStateException("teardown_start_barrier_timeout");
                        results[slot] = new Type111ControlClient(compositorEndpoint)
                                .parentTeardown(owner);
                    } catch (Throwable failure) { failures[slot] = failure; }
                    finally { done.countDown(); }
                }
            }, "ClarityLinkReentrantTeardown-" + index).start();
        }
        if (!ready.await(5L, TimeUnit.SECONDS)) {
            start.countDown();
            control.releaseLabParentTeardownBarrier(owner);
            throw new IllegalStateException("teardown_workers_not_ready");
        }
        start.countDown();
        boolean firstPaused = false;
        boolean contenderRejectedWhilePaused = false;
        try {
            firstPaused = control.awaitLabParentTeardownBarrier(owner, false, 5000L);
            contenderRejectedWhilePaused = firstPaused &&
                    control.awaitLabParentTeardownBarrier(owner, true, 5000L);
            if (firstPaused) {
                FrameStreamIdentity replacement = child.withGeneration(child.streamGeneration + 1L);
                if (control.setup(replacement) ||
                        new FrameIpcClient(compositorEndpoint).begin(replacement, new Binder()) >= 0)
                    throw new IllegalStateException("stream_registration_accepted_during_parent_shutdown");
                Type111ControlClient.FrameStats beforeRelease = control.queryFrameStats(child);
                if (beforeRelease == null || !beforeRelease.registered ||
                        beforeRelease.activePfdTransfers != 1 || beforeRelease.retainedFrameBytes != 0)
                    throw new IllegalStateException("shutdown_registration_attempt_changed_current_stream");
                Log.i(TAG, "CL_R4B_TEARDOWN_REGISTRATION_REJECTED session_id=" + owner.sessionId +
                        " proposed_generation=" + replacement.streamGeneration +
                        " current_registration_preserved=true active_pfd=1");
                boolean replacementAccepted = FrameIpcClient.replaceType111Sink(compositorEndpoint,
                        owner, child, replacement, new Binder());
                if (replacementAccepted)
                    throw new IllegalStateException("replacement_registered_during_parent_shutdown");
                Log.i(TAG, "CL_R4B_TEARDOWN_REPLACEMENT_REJECTED session_id=" + owner.sessionId +
                        " old_generation=" + child.streamGeneration +
                        " proposed_generation=" + replacement.streamGeneration +
                        " replacement_unchanged=true");
                if (!controlBarrier(FrameIpcProtocol.LAB_RELEASE_TRANSFER_BARRIER, child, 0L) ||
                        !controlBarrier(FrameIpcProtocol.LAB_WAIT_TRANSFER_FINISHED, child, 5000L) ||
                        !transferDone.await(5L, TimeUnit.SECONDS))
                    throw new IllegalStateException("pending_teardown_transfer_did_not_finish");
                if (transferAccepted[0] || !"session_closing".equals(transferReason[0]))
                    throw new IllegalStateException("pending_frame_not_rejected_after_admission_closed:" +
                            transferReason[0]);
                int[] transferStats = queryType111TransferStats(child);
                if (transferStats[0] != 0 || transferStats[1] != 0 || transferStats[2] != 0)
                    throw new IllegalStateException("pending_teardown_transfer_resources_retained");
                Log.i(TAG, "CL_R4B_TEARDOWN_PENDING_PFD_REJECTED session_id=" + owner.sessionId +
                        " result=" + transferReason[0] + " active_pfd=0 retained_bytes=0 " +
                        "transfer_active=false");
                killType110SinkForTeardownRace(owner);
            }
        } finally { control.releaseLabParentTeardownBarrier(owner); }
        if (!firstPaused || !contenderRejectedWhilePaused) {
            done.await(8L, TimeUnit.SECONDS);
            throw new IllegalStateException("teardown_calls_did_not_overlap_admission_close");
        }
        if (!done.await(8L, TimeUnit.SECONDS))
            throw new IllegalStateException("concurrent_parent_teardown_timeout");
        if (failures[0] != null || failures[1] != null || results[0] == results[1])
            throw new IllegalStateException("concurrent_parent_teardown_result_mismatch");
        if (control.parentTeardown(owner))
            throw new IllegalStateException("repeated_parent_teardown_changed_state");
        Type111ControlClient.StreamQuery query = control.queryType111Stream(owner);
        Type111ControlClient.FrameStats ownerStats = control.queryFrameStats(owner);
        Type111ControlClient.FrameStats childStats = control.queryFrameStats(child);
        if (query == null || query.ownerValid || query.identity != null || query.sinkAttached ||
                !zeroUnregistered(ownerStats) || !zeroUnregistered(childStats))
            throw new IllegalStateException("reentrant_parent_teardown_left_resources");
        reentrantTeardownInProgress = false;
        Log.i(TAG, "CL_R4B_REENTRANT_PARENT_TEARDOWN_PASS session_id=" + owner.sessionId +
                " concurrent_calls=2 accepted_calls=1 rejected_calls=1 repeated_close_rejected=true " +
                "overlap_barrier=first_paused_contender_rejected " +
                "pending_pfd_rejected=true registration_during_shutdown_rejected=true " +
                "replacement_during_shutdown_rejected=true type110_died_during_shutdown=true " +
                "owner_valid=false child_present=false pfd_transfers=0 retained_bytes=0");
    }

    /** Kill the real separate Type110 sink only after teardown has closed session admission. */
    private void killType110SinkForTeardownRace(final FrameStreamIdentity owner) throws Exception {
        final CountDownLatch died = new CountDownLatch(1);
        FrameLabSink.Stats stats = queryType110StatsOrThrow("type110_teardown_race_stats_missing");
        if (stats.pid <= 0 || primaryLabSinkBinder == null || !primaryLabSinkBinder.isBinderAlive())
            throw new IllegalStateException("type110_teardown_race_process_missing");
        try {
            primaryLabSinkBinder.linkToDeath(new IBinder.DeathRecipient() {
                public void binderDied() { died.countDown(); }
            }, 0);
        } catch (android.os.RemoteException alreadyDead) {
            throw new IllegalStateException("type110_sink_died_before_teardown_race");
        }
        Intent failure = new Intent(this, Type110SinkFailureTestService.class);
        failure.putExtra("confirmation", "CL_R4B_OFFLINE_EMULATOR_ONLY");
        failure.putExtra("target_pid", stats.pid);
        failure.putExtra("target_session_id", owner.sessionId);
        if (startService(failure) == null || !died.await(5L, TimeUnit.SECONDS))
            throw new IllegalStateException("type110_sink_did_not_die_during_teardown");
        Log.i(TAG, "CL_R4B_TEARDOWN_TYPE110_DEATH_PASS session_id=" + owner.sessionId +
                " sink_pid=" + stats.pid + " binder_death_observed=true admission_already_closed=true");
    }

    private static boolean zeroUnregistered(Type111ControlClient.FrameStats stats) {
        return stats != null && !stats.registered && stats.activePfdTransfers == 0 &&
                stats.retainedFrameBytes == 0 && !stats.transferActive && stats.lastFrameId == 0L;
    }

    private byte[] type111Fixture(String name) throws Exception {
        InputStream input = getAssets().open(name);
        ByteArrayOutputStream encoded = new ByteArrayOutputStream();
        byte[] buffer = new byte[1024];
        int count;
        while ((count = input.read(buffer)) != -1) {
            if (encoded.size() + count > 16384) throw new IllegalStateException("type111_fixture_size_limit");
            encoded.write(buffer, 0, count);
        }
        input.close();
        return Base64.decode(encoded.toByteArray(), Base64.DEFAULT);
    }

    /** Decoder process death/restart uses the genuine Binder v3 stream and existing View sink. */
    private void runIndependentType111ProducerFault(Api17BufferH264Decoder type110Decoder,
            byte[][] type110AccessUnits, long binderGeneration) throws Exception {
        final String descriptor = "org.claritylink.android.IType111LabProducer";
        final IBinder[] producerBinder = new IBinder[1];
        final boolean[] producerBound = new boolean[1];
        final ServiceConnection[] recoveryConnection = new ServiceConnection[1];
        final boolean[] recoveryBound = new boolean[1];
        final CountDownLatch firstConnection = new CountDownLatch(1);
        final CountDownLatch death = new CountDownLatch(1);
        ServiceConnection connection = new ServiceConnection() {
            public void onServiceConnected(ComponentName name, IBinder service) {
                producerBinder[0] = service;
                firstConnection.countDown();
            }
            public void onServiceDisconnected(ComponentName name) {
                death.countDown();
                log("TYPE111_PRODUCER_BINDER_DEATH_CALLBACK component=" + name.getClassName());
            }
        };
        if (!bindService(new Intent(this, Type111ProducerService.class), connection,
                Context.BIND_AUTO_CREATE)) throw new IllegalStateException("type111_producer_bind_failed");
        producerBound[0] = true;
        try {
            requireType111(awaitRace(firstConnection), "independent_type111_producer_service_bound");
            verifyProducerWaitBounds(producerBinder[0], descriptor);
            FrameStreamIdentity before = frameIpcClient.streamIdentity();
            FrameLabSink.Stats type110Before = queryType110StatsOrThrow("type110_stats_before_producer_death");
            int oldPid = startIsolatedProducer(producerBinder[0], descriptor, before,
                    frameIpcClient.nextFrameIdHint(), 9000000L);
            requireType111(oldPid > 0 && oldPid != android.os.Process.myPid() &&
                    oldPid != compositorRemotePid && oldPid != type110Before.pid,
                    "producer_view_compositor_type110_processes_are_distinct");
            long[] firstProducerFrames = awaitIsolatedProducerFrames(producerBinder[0], descriptor);
            requireType111(firstProducerFrames.length >= 2, "isolated_producer_decoded_two_h264_frames");
            requireType111(awaitViewFrameDrawn(binderGeneration,
                    firstProducerFrames[firstProducerFrames.length - 1]),
                    "isolated_producer_latest_h264_frame_drawn");
            captureType111Proof("type111-independent-producer-frame.png");
            Log.i(TAG, "TYPE111_PRODUCER_PROCESS_TO_VIEW_PASS component=Type111ProducerService " +
                    "process=:type111_producer pid=" + oldPid + " view_pid=" + android.os.Process.myPid() +
                    " compositor_pid=" + compositorRemotePid + " type110_sink_pid=" + type110Before.pid +
                    " binder_v3=true decoder=MediaCodec");

            requireType111(controlBarrier(FrameIpcProtocol.LAB_ARM_TRANSFER_BARRIER, before, 0L),
                    "arm_actual_inflight_pfd_barrier");
            requireType111(startIsolatedProducer(producerBinder[0], descriptor, before,
                    frameIpcClient.nextFrameIdHint(), 11000000L) == oldPid,
                    "producer_second_decode_run_started_in_same_process");
            requireType111(controlBarrier(FrameIpcProtocol.LAB_WAIT_TRANSFER_BARRIER, before, 10000L),
                    "compositor_holds_live_type111_pfd_before_read");
            int[] heldStats = queryType111TransferStats(before);
            requireType111(heldStats[0] == 1 && heldStats[1] == 0 && heldStats[2] == 1,
                    "inflight_pfd_is_owned_and_counted_before_producer_death");
            FrameLabSink.Stats type110DuringBlocked = queryType110StatsOrThrow(
                    "type110_stats_before_blocked_transfer_probe");
            submitType110DecodedFrame(decodeFixtureFrame(type110Decoder, type110AccessUnits,
                    970001L, 3500000L, 3000000000L), binderGeneration);
            FrameLabSink.Stats type110WhileBlocked = queryType110StatsOrThrow(
                    "type110_stats_while_type111_pfd_blocked");
            requireType111(type110WhileBlocked.frameId > type110DuringBlocked.frameId,
                    "type110_progressed_while_type111_pfd_transfer_blocked");
            Log.i(TAG, "CL_R4_TYPE110_DURING_TYPE111_PFD_BLOCK_PASS before=" +
                    type110DuringBlocked.frameId + " after=" + type110WhileBlocked.frameId);

            Parcel killData = Parcel.obtain();
            Parcel killReply = Parcel.obtain();
            boolean killAccepted;
            try {
                killData.writeInterfaceToken(descriptor);
                producerBinder[0].transact(IBinder.FIRST_CALL_TRANSACTION + 1, killData, killReply, 0);
                killReply.readException();
                killAccepted = killReply.readInt() != 0 && killReply.readInt() == oldPid;
            } finally { killReply.recycle(); killData.recycle(); }
            requireType111(killAccepted && awaitRace(death),
                    "actual_type111_producer_death_and_binder_callback");
            requireType111(controlBarrier(FrameIpcProtocol.LAB_RELEASE_TRANSFER_BARRIER, before, 0L),
                    "release_compositor_after_producer_process_death");
            requireType111(controlBarrier(FrameIpcProtocol.LAB_WAIT_TRANSFER_FINISHED, before, 10000L),
                    "inflight_transfer_finishes_after_pipe_writer_death");
            int[] cleanedStats = queryType111TransferStats(before);
            requireType111(cleanedStats[0] == 0 && cleanedStats[1] == 0 && cleanedStats[2] == 0 &&
                    cleanedStats[3] == heldStats[3],
                    "inflight_pfd_eof_cleanup_without_accepting_partial_frame");
            Log.i(TAG, "CL_R4_TYPE111_INFLIGHT_PRODUCER_DEATH_CLEANUP_PASS " +
                    "active_pfd=" + cleanedStats[0] + " retained_bytes=" + cleanedStats[1] +
                    " transfer_active=" + cleanedStats[2] + " last_frame_unchanged=true");

            FrameLabSink.Stats atDeath = queryType110StatsOrThrow("type110_stats_at_producer_death");
            DecodedFrame type110AfterDeath = decodeFixtureFrame(type110Decoder, type110AccessUnits,
                    970001L, 4500000L, 4000000000L);
            submitType110DecodedFrame(type110AfterDeath, binderGeneration);
            FrameLabSink.Stats afterType110 = queryType110StatsOrThrow("type110_stats_after_producer_death");
            requireType111(afterType110.frameId > atDeath.frameId,
                    "type110_frame_progressed_after_actual_type111_producer_death");
            Log.i(TAG, "CL_R4_TYPE110_AFTER_TYPE111_PRODUCER_DEATH_PASS producer_pid=" + oldPid +
                    " frame_at_death=" + atDeath.frameId + " frame_after_death=" + afterType110.frameId);

            requireType111(awaitRace(death), "producer_binding_death_callback_observed");
            FrameStreamIdentity oldIdentity = frameIpcClient.streamIdentity();
            long freshGeneration = oldIdentity.streamGeneration + 1L;
            requireType111(frameIpcClient.replaceGeneration(oldIdentity.streamGeneration, freshGeneration),
                    "type111_generation_invalidated_after_producer_death");
            FrameStreamIdentity freshIdentity = frameIpcClient.streamIdentity();
            requireType111(freshIdentity.sessionId == oldIdentity.sessionId &&
                    freshIdentity.connectionId == oldIdentity.connectionId &&
                    freshIdentity.streamGeneration == freshGeneration,
                    "producer_restart_preserves_parent_connection_and_advances_generation");
            requireType111("frame_contract_rejected".equals(frameIpcClient.probeMalformed(
                    "stale_generation", freshGeneration, 9200000000L)),
                    "predeath_type111_generation_rejected_after_restart");
            // API17 reports the dead binding but does not consistently reconnect a bound-only
            // service. Rebind only after the actual death callback, so recovery is explicit and
            // its replacement process can be identified without a polling sleep.
            unbindService(connection);
            producerBound[0] = false;
            producerBinder[0] = null;
            final CountDownLatch restarted = new CountDownLatch(1);
            recoveryConnection[0] = new ServiceConnection() {
                public void onServiceConnected(ComponentName name, IBinder service) {
                    producerBinder[0] = service;
                    restarted.countDown();
                }
                public void onServiceDisconnected(ComponentName name) {
                    log("TYPE111_PRODUCER_RECOVERY_BINDER_DISCONNECTED component=" +
                            name.getClassName());
                }
            };
            requireType111(bindService(new Intent(this, Type111ProducerService.class), recoveryConnection[0],
                    Context.BIND_AUTO_CREATE), "type111_producer_rebind_accepted_after_death");
            recoveryBound[0] = true;
            requireType111(awaitRace(restarted), "producer_rebound_after_process_death");
            Log.i(TAG, "CL_R4_TYPE111_PRODUCER_REBIND_PASS old_pid=" + oldPid +
                    " binder_death_observed=true previous_binding_released=true new_binding_connected=true");
            IBinder freshProducerBinder = producerBinder[0];
            int freshPid = queryIsolatedProducerPid(freshProducerBinder, descriptor);
            requireType111(freshPid > 0 && freshPid != oldPid && freshPid != android.os.Process.myPid(),
                    "restarted_producer_has_new_process_identity");
            requireType111(new Type111ControlClient(compositorEndpoint).videoConfig(
                    freshIdentity, 32, 32) > 0, "video_config_rebound_for_fresh_generation");
            startIsolatedProducer(freshProducerBinder, descriptor, freshIdentity,
                    frameIpcClient.nextFrameIdHint(), 10000000L);
            long[] restartedFrames = awaitIsolatedProducerFrames(freshProducerBinder, descriptor);
            requireType111(restartedFrames.length >= 2, "restarted_producer_decoded_two_h264_frames");
            requireType111(awaitViewFrameDrawn(binderGeneration,
                    restartedFrames[restartedFrames.length - 1]),
                    "restarted_type111_producer_latest_frame_drawn");
            captureType111Proof("type111-restarted-producer-frame.png");
            Log.i(TAG, "CL_R4_TYPE111_PRODUCER_DEATH_RESTART_PASS old_pid=" + oldPid +
                    " new_pid=" + freshPid + " old_generation=" + oldIdentity.streamGeneration +
                    " new_generation=" + freshIdentity.streamGeneration + " stale_rejected=true " +
                    "type110_progress_after_death=true h264_decoded=true binder_pfd=true view_draw=true");
        } finally {
            if (producerBound[0]) {
                try { unbindService(connection); } catch (IllegalArgumentException ignored) { }
            }
            if (recoveryBound[0]) {
                try { unbindService(recoveryConnection[0]); } catch (IllegalArgumentException ignored) { }
            }
        }
    }

    private int startIsolatedProducer(IBinder producer, String descriptor,
            FrameStreamIdentity identity, long nextFrameId, long firstPtsUs) throws Exception {
        Parcel data = Parcel.obtain();
        Parcel reply = Parcel.obtain();
        try {
            data.writeInterfaceToken(descriptor);
            data.writeStrongBinder(compositorEndpoint);
            data.writeStrongBinder(viewSink);
            data.writeLong(identity.sessionId);
            data.writeInt(identity.streamType);
            data.writeLong(identity.connectionId);
            data.writeLong(identity.streamGeneration);
            data.writeInt(identity.outputId);
            data.writeLong(nextFrameId);
            data.writeLong(firstPtsUs + fixtureTimestampOffsetNs / 1000L);
            producer.transact(IBinder.FIRST_CALL_TRANSACTION, data, reply, 0);
            reply.readException();
            boolean accepted = reply.readInt() != 0;
            int pid = reply.readInt();
            if (!accepted) throw new IllegalStateException("isolated_type111_producer_rejected");
            return pid;
        } finally { reply.recycle(); data.recycle(); }
    }

    private int queryIsolatedProducerPid(IBinder producer, String descriptor) throws Exception {
        Parcel data = Parcel.obtain();
        Parcel reply = Parcel.obtain();
        try {
            data.writeInterfaceToken(descriptor);
            producer.transact(IBinder.FIRST_CALL_TRANSACTION + 2, data, reply, 0);
            reply.readException();
            int pid = reply.readInt();
            reply.readInt(); reply.readInt();
            return pid;
        } finally { reply.recycle(); data.recycle(); }
    }

    private long[] awaitIsolatedProducerFrames(IBinder producer, String descriptor) throws Exception {
        // Each Binder wait remains capped by the producer's 15s contract. Retry only
        // after an explicit unfinished reply, for a bounded total of 45s; this avoids
        // treating slow API17 codec startup as a producer failure or using blind sleeps.
        for (int attempt = 0; attempt < 3; attempt++) {
            Parcel data = Parcel.obtain();
            Parcel reply = Parcel.obtain();
            try {
                data.writeInterfaceToken(descriptor);
                data.writeLong(15000L);
                producer.transact(IBinder.FIRST_CALL_TRANSACTION + 3, data, reply, 0);
                reply.readException();
                boolean finished = reply.readInt() != 0;
                int count = reply.readInt();
                if (count < 0 || count > 4)
                    throw new IllegalStateException("isolated_producer_completion_count_invalid");
                if (finished) {
                    long[] timestamps = new long[count];
                    for (int i = 0; i < count; i++) timestamps[i] = reply.readLong();
                    return timestamps;
                }
            } finally { reply.recycle(); data.recycle(); }
        }
        throw new IllegalStateException("isolated_producer_did_not_finish_within_bounded_waits");
    }

    private boolean controlBarrier(int code, FrameStreamIdentity identity, long timeoutMs)
            throws Exception {
        Parcel data = Parcel.obtain();
        Parcel reply = Parcel.obtain();
        try {
            data.writeInterfaceToken(FrameIpcProtocol.DESCRIPTOR);
            data.writeInt(FrameIpcProtocol.VERSION);
            data.writeLong(identity.sessionId);
            data.writeInt(identity.streamType);
            data.writeLong(identity.connectionId);
            data.writeLong(identity.streamGeneration);
            data.writeInt(identity.outputId);
            if (code == FrameIpcProtocol.LAB_WAIT_TRANSFER_BARRIER ||
                    code == FrameIpcProtocol.LAB_WAIT_TRANSFER_FINISHED) data.writeLong(timeoutMs);
            compositorEndpoint.transact(code, data, reply, 0);
            reply.readException();
            return reply.readInt() != 0;
        } finally { reply.recycle(); data.recycle(); }
    }

    private int[] queryType111TransferStats(FrameStreamIdentity identity) throws Exception {
        Parcel data = Parcel.obtain();
        Parcel reply = Parcel.obtain();
        try {
            data.writeInterfaceToken(FrameIpcProtocol.DESCRIPTOR);
            data.writeInt(FrameIpcProtocol.VERSION);
            data.writeLong(identity.sessionId);
            data.writeInt(identity.streamType);
            data.writeLong(identity.connectionId);
            data.writeLong(identity.streamGeneration);
            data.writeInt(identity.outputId);
            compositorEndpoint.transact(FrameIpcProtocol.FRAME_LAB_QUERY_STATS, data, reply, 0);
            reply.readException();
            boolean matches = reply.readInt() != 0;
            int[] stats = new int[] { reply.readInt(), reply.readInt(), reply.readInt() };
            long lastFrameId = reply.readLong();
            if (!matches || lastFrameId > Integer.MAX_VALUE)
                throw new IllegalStateException("type111_transfer_stats_identity_invalid");
            return new int[] { stats[0], stats[1], stats[2], (int) lastFrameId };
        } finally { reply.recycle(); data.recycle(); }
    }

    private void verifyProducerWaitBounds(IBinder producer, String descriptor) throws Exception {
        long[] invalidTimeouts = new long[] { -1L, Long.MAX_VALUE };
        for (long timeout : invalidTimeouts) {
            Parcel data = Parcel.obtain();
            Parcel reply = Parcel.obtain();
            try {
                data.writeInterfaceToken(descriptor);
                data.writeLong(timeout);
                producer.transact(IBinder.FIRST_CALL_TRANSACTION + 3, data, reply, 0);
                reply.readException();
                if (reply.readInt() != 0 || reply.readInt() != 0)
                    throw new IllegalStateException("producer_wait_timeout_bound_not_enforced:" + timeout);
            } finally { reply.recycle(); data.recycle(); }
        }
        Log.i(TAG, "TYPE111_PRODUCER_WAIT_BOUNDS_PASS negative_and_oversized_rejected=true");
    }

    private void submitDecodedFrame(final DecodedFrame frame, final long binderGeneration,
            boolean verifyBackpressure) {
        submitDecodedFrame(frame, binderGeneration, verifyBackpressure, frameIpcClient, false);
    }

    private void submitType110DecodedFrame(final DecodedFrame frame, long binderGeneration) {
        FrameIpcClient client = primaryLabIpcClient;
        IBinder sink = primaryLabSinkBinder;
        requireType111(client != null && sink != null, "type110_primary_lab_ipc_registered");
        FrameLabSink.Stats before;
        try { before = FrameLabSink.queryStats(sink); }
        catch (android.os.DeadObjectException ownerSinkDied) {
            if (type110SinkFailureTest)
                throw new ExpectedType110SinkLoss(client.streamIdentity().sessionId, ownerSinkDied);
            throw new IllegalStateException("type110_sink_stats_unavailable", ownerSinkDied);
        }
        catch (Exception failure) { throw new IllegalStateException("type110_sink_stats_unavailable", failure); }
        if (before == null && type110SinkFailureTest && sink != null && !sink.isBinderAlive())
            throw new ExpectedType110SinkLoss(client.streamIdentity().sessionId, null);
        requireType111(before != null, "type110_sink_stats_available_over_binder");
        FrameStreamIdentity identity = client.streamIdentity();
        requireType111(identity != null && identity.sessionId == binderGeneration,
                "type110_stream_session_matches_shared_binder_session");
        submitDecodedFrame(frame, identity.streamGeneration, false, client, true);
        FrameLabSink.Stats after;
        try { after = FrameLabSink.queryStats(sink); }
        catch (android.os.DeadObjectException ownerSinkDied) {
            if (type110SinkFailureTest)
                throw new ExpectedType110SinkLoss(identity.sessionId, ownerSinkDied);
            throw new IllegalStateException("type110_sink_stats_unavailable", ownerSinkDied);
        }
        catch (Exception failure) { throw new IllegalStateException("type110_sink_stats_unavailable", failure); }
        if (after == null && type110SinkFailureTest && sink != null && !sink.isBinderAlive())
            throw new ExpectedType110SinkLoss(identity.sessionId, null);
        requireType111(after != null && after.frames == before.frames + 1,
                "type110_frame_recorded_by_primary_lab_sink_not_type111_view");
        Log.i(TAG, "CL_R4_TYPE110_BINDER_FRAME_ROUTED stream_type=110 output_id=1 " +
                "sink_pid=" + after.pid + " frame_id=" + after.frameId + " checksum=" + after.checksum);
    }

    private FrameLabSink.Stats queryType110StatsOrThrow(String failureCode) {
        try {
            FrameLabSink.Stats stats = FrameLabSink.queryStats(primaryLabSinkBinder);
            if (stats == null) throw new IllegalStateException(failureCode);
            return stats;
        } catch (android.os.RemoteException failure) {
            throw new IllegalStateException(failureCode, failure);
        }
    }

    private void issueType110ProbeOwnership(FrameStreamIdentity identity,
            FrameLabSink.Stats stats) {
        FrameStreamIdentity expectedType111Death = frameIpcClient == null ? null :
                frameIpcClient.streamIdentity();
        if (stats == null || type111ControlClient == null ||
                !type111ControlClient.registerType110Recovery(identity,
                        expectedType111Death, stats.frameId, stats.pid))
            throw new IllegalStateException("type110_probe_owner_record_not_issued");
        log("TYPE110_PROBE_OWNER_RECORD_ISSUED session_id=" + identity.sessionId +
                " connection_id=" + identity.connectionId +
                " stream_generation=" + identity.streamGeneration +
                " output_id=" + identity.outputId + " owner=compositor_memory_receipt");
    }

    /** Holds the Type111 Handler at a known frame, fills its View queue, then verifies Type110 progress. */
    private void runApi17DualStreamSaturation(DecodedFrame decodedType111,
            DecodedFrame decodedType110, long binderGeneration) throws Exception {
        requireType111(decodedType111 != null && decodedType110 != null,
                "dual_stream_saturation_uses_decoded_fixture_frames");
        final long baseTimestamp = fixtureTimestamp(5000000000L);
        final DecodedFrame handlerBarrierFrame = withTimestamp(decodedType111, baseTimestamp);
        final FrameViewSink.TestControl control = new FrameViewSink.TestControl();
        control.pauseHandlerAt(handlerBarrierFrame.presentationTimeNs);
        control.expectDispatchCount(FrameViewSink.MAX_QUEUED_FRAMES);
        viewSink.setDispatchProbe(control);
        try {
            String first = submitForReceipt(frameIpcClient, handlerBarrierFrame, binderGeneration);
            requireType111("accepted".equals(first), "first_type111_frame_accepted_before_handler_barrier");
            requireType111(awaitRace(control.handlerEntered), "type111_handler_paused_at_exact_frame");

            DecodedFrame secondFrame = withTimestamp(decodedType111,
                    baseTimestamp + 100000000L);
            DecodedFrame thirdFrame = withTimestamp(decodedType111,
                    baseTimestamp + 200000000L);
            String second = submitForReceipt(frameIpcClient, secondFrame, binderGeneration);
            String third = submitForReceipt(frameIpcClient, thirdFrame, binderGeneration);
            requireType111("accepted".equals(second) && "accepted".equals(third),
                    "type111_bounded_pending_frames_accepted");
            requireType111(viewSink.queuedFrameCount() == FrameViewSink.MAX_QUEUED_FRAMES,
                    "type111_queue_saturated_at_declared_frame_limit");

            String overflow = submitForReceipt(frameIpcClient,
                    withTimestamp(decodedType111, baseTimestamp + 300000000L), binderGeneration);
            requireType111("frame_dispatch_queue_full".equals(overflow),
                    "type111_overflow_rejected_without_retention");
            requireType111(viewSink.queuedFrameCount() == FrameViewSink.MAX_QUEUED_FRAMES,
                    "type111_queue_remains_within_bound_after_overflow");

            FrameStreamIdentity primaryBefore = primaryLabIpcClient.streamIdentity();
            FrameStreamIdentity secondaryBefore = frameIpcClient.streamIdentity();
            requireType111(primaryBefore != null && secondaryBefore != null &&
                    primaryBefore.sessionId == secondaryBefore.sessionId,
                    "both_streams_share_one_binder_session_identity");
            long newPrimaryGeneration = primaryBefore.streamGeneration + 1L;
            if (reattachSessionId <= 0L) {
                requireType111(primaryLabIpcClient.replaceGeneration(primaryBefore.streamGeneration,
                        newPrimaryGeneration), "type110_live_generation_change_accepted");
            } else {
                requireType111(primaryBefore.streamGeneration == reattachType110Generation,
                        "type110_identity_unchanged_since_type111_sink_replacement");
            }
            requireType111(frameIpcClient.streamIdentity().streamGeneration == secondaryBefore.streamGeneration,
                    "type110_generation_change_does_not_change_type111_generation");
            String stalePrimary = primaryLabIpcClient.probeMalformed("stale_generation",
                    newPrimaryGeneration, 1400000001L);
            requireType111("frame_contract_rejected".equals(stalePrimary),
                    "stale_type110_generation_rejected_by_actual_binder_receiver");
            Log.i(TAG, "CL_R4_STREAM_GENERATION_ISOLATION_PASS session_id=" + primaryBefore.sessionId +
                    " stream_type=110 old=" + primaryBefore.streamGeneration +
                    " new=" + (reattachSessionId <= 0L ? newPrimaryGeneration : primaryBefore.streamGeneration) +
                    " stream_type_111_generation=" +
                    secondaryBefore.streamGeneration + " binder_pid_preserved=true stale_rejected=true");

            submitType110DecodedFrame(decodedType110, binderGeneration);
            FrameLabSink.Stats type110Progress = FrameLabSink.queryStats(primaryLabSinkBinder);
            requireType111(type110Progress != null && type110Progress.frameId > 0,
                    "type110_progressed_while_type111_handler_blocked");
            requireType111(viewSink.queuedFrameCount() == FrameViewSink.MAX_QUEUED_FRAMES,
                    "type110_did_not_consume_or_change_type111_queue");

            control.releaseHandler.countDown();
            requireType111(awaitRace(control.dispatchFinished), "all_accepted_type111_queue_entries_drained");
            long finalTimestamp = thirdFrame.presentationTimeNs;
            requireType111(awaitViewFrameDrawn(binderGeneration, finalTimestamp),
                    "latest_accepted_type111_frame_drawn_after_release");
            requireType111(viewSink.queuedFrameCount() == 0,
                    "type111_queue_released_all_retained_frames");
            requireType111(renderer != null && renderer.contentView().drawnTimestampNs() == finalTimestamp,
                    "primary_type110_frame_never_cross_routed_to_secondary_view");
            Log.i(TAG, "CL_R4_API17_DUAL_STREAM_SATURATION_PASS session_id=" + binderGeneration +
                    " type111_limit_frames=" + FrameViewSink.MAX_QUEUED_FRAMES +
                    " type111_limit_bytes=" + FrameViewSink.MAX_QUEUED_FRAME_BYTES +
                    " type111_queue_full_rejected=true type110_progress_before_release=true " +
                    "cross_route=false drain_policy=reject_new_and_drain_accepted");
        } finally {
            control.releaseHandler.countDown();
            viewSink.setDispatchProbe(null);
        }
    }

    private String submitForReceipt(FrameIpcClient client, DecodedFrame frame, long generation)
            throws InterruptedException {
        final CountDownLatch completed = new CountDownLatch(1);
        final String[] receipt = new String[] { "submission_not_started" };
        FrameStreamIdentity identity = client == null ? null : client.streamIdentity();
        long streamGeneration = identity == null ? generation : identity.streamGeneration;
        boolean started = client != null && client.submit(frame, streamGeneration, new FrameIpcClient.Callback() {
            public void complete(boolean accepted, String reason) {
                receipt[0] = accepted ? "accepted" : reason;
                completed.countDown();
            }
        });
        if (!started) return receipt[0];
        if (!awaitRace(completed)) return "callback_timeout";
        return receipt[0];
    }

    private DecodedFrame withTimestamp(DecodedFrame frame, long timestampNs) throws Exception {
        long monotonicTimestamp = Math.max(timestampNs,
                lastType111SubmissionTimestampNs + 1L);
        lastType111SubmissionTimestampNs = monotonicTimestamp;
        return copyWithTimestamp(frame, monotonicTimestamp);
    }

    private DecodedFrame copyWithTimestamp(DecodedFrame frame, long timestampNs) throws Exception {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream(frame.byteSize());
        frame.writeRgbaTo(bytes);
        return new DecodedFrame(frame.width, frame.height, frame.rowStride,
                timestampNs,
                frame.rotationDegrees, frame.cropLeft, frame.cropTop, frame.cropRight,
                frame.cropBottom, ByteBuffer.wrap(bytes.toByteArray()));
    }

    private void submitDecodedFrame(final DecodedFrame frame, final long binderGeneration,
            boolean verifyBackpressure, FrameIpcClient client, boolean primaryLabOutput) {
        final DecodedFrame submittedFrame;
        try {
            if (primaryLabOutput) submittedFrame = frame;
            else {
                long timestamp = Math.max(frame.presentationTimeNs,
                        lastType111SubmissionTimestampNs + 1L);
                submittedFrame = timestamp == frame.presentationTimeNs ? frame :
                        copyWithTimestamp(frame, timestamp);
                lastType111SubmissionTimestampNs = timestamp;
            }
        } catch (Exception failure) {
            throw new IllegalStateException("type111_monotonic_timestamp_copy_failed", failure);
        }
        final CountDownLatch completed = new CountDownLatch(1);
        final boolean[] accepted = new boolean[] { false };
        FrameStreamIdentity identity = client == null ? null : client.streamIdentity();
        final long streamGeneration = identity == null ? -1L : identity.streamGeneration;
        requireType111(client != null && client.submit(submittedFrame, streamGeneration,
                new FrameIpcClient.Callback() {
                    public void complete(boolean value, String reason) {
                        accepted[0] = value;
                        if (!value) log("CL_R4_BINDER_FRAME_REJECT timestamp=" +
                                submittedFrame.presentationTimeNs + " reason=" + reason);
                        completed.countDown();
                    }
                }), "decoded_frame_submitted_to_real_binder_pfd");
        if (verifyBackpressure) {
            final boolean[] rejected = new boolean[] { false };
            boolean started = client.submit(submittedFrame, streamGeneration, new FrameIpcClient.Callback() {
                public void complete(boolean accepted, String reason) {
                    rejected[0] = !accepted && "backpressure".equals(reason);
                }
            });
            requireType111(!started && rejected[0], "bounded_single_flight_backpressure");
        }
        requireType111(awaitRace(completed) && accepted[0], "decoded_frame_accepted_by_remote_receiver");
        if (!primaryLabOutput) {
            requireType111(awaitViewFrameDrawn(activeGeneration, submittedFrame.presentationTimeNs),
                    "decoded_frame_drawn_by_actual_view");
            Log.i(TAG, "CL_R4_DECODED_FRAME_DRAWN width=" + frame.width + " height=" + frame.height +
                    " timestamp_ns=" + submittedFrame.presentationTimeNs + " stream_generation=" + streamGeneration +
                    " parent_display_generation=" + activeGeneration);
        }
    }

    private int[] readDecodedCenterRgb(DecodedFrame frame) throws Exception {
        ByteArrayOutputStream pixels = new ByteArrayOutputStream(frame.byteSize());
        frame.writeRgbaTo(pixels);
        byte[] rgba = pixels.toByteArray();
        int offset = (frame.height / 2 * frame.width + frame.width / 2) * 4;
        return new int[] { rgba[offset] & 255, rgba[offset + 1] & 255, rgba[offset + 2] & 255 };
    }

    /** Synthetic adapter integration vector: padded planar rows/slices and a nonzero red crop. */
    private DecodedFrame paddedCropFixtureFrame(long timestampNs) {
        int width = 32, height = 32, stride = 40, slice = 40;
        int chromaStride = 20, chromaRows = 20, yBytes = stride * slice;
        int chromaBytes = chromaStride * chromaRows;
        byte[] yuv = new byte[yBytes + chromaBytes * 2];
        java.util.Arrays.fill(yuv, (byte) 16);
        for (int y = 0; y < height; y++)
            java.util.Arrays.fill(yuv, y * stride, y * stride + width, (byte) 81);
        java.util.Arrays.fill(yuv, yBytes, yBytes + chromaBytes, (byte) 128);
        java.util.Arrays.fill(yuv, yBytes + chromaBytes, yuv.length, (byte) 128);
        for (int y = 8; y < 24; y += 2) for (int x = 8; x < 24; x += 2) {
            int sample = yBytes + (y / 2) * chromaStride + x / 2;
            yuv[sample] = (byte) 90;
            yuv[yBytes + chromaBytes + (y / 2) * chromaStride + x / 2] = (byte) 240;
        }
        return Yuv420FrameAdapter.convert(yuv, 0, yuv.length, width, height, stride, slice,
                android.media.MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Planar,
                8, 8, 24, 24, timestampNs);
    }

    private DecodedFrame decodeFixtureFrame(Api17BufferH264Decoder decoder,
            byte[][] accessUnits, long generation, long firstPtsUs, long minimumTimestampNs) {
        firstPtsUs += fixtureTimestampOffsetNs / 1000L;
        minimumTimestampNs += fixtureTimestampOffsetNs;
        for (int index = 0; index < 16; index++) {
            DecodedFrame frame = decoder.decode(accessUnits[index % accessUnits.length],
                    firstPtsUs + index * 100000L, generation, 3000L);
            if (frame != null && frame.presentationTimeNs > minimumTimestampNs) return frame;
        }
        throw new IllegalStateException("type110_fixture_decoder_no_output");
    }

    private long fixtureTimestamp(long timestampNs) {
        return timestampNs + fixtureTimestampOffsetNs;
    }

    private long fixturePtsUs(long ptsUs) {
        return ptsUs + fixtureTimestampOffsetNs / 1000L;
    }

    /** Deterministic fault hook used only by the explicitly requested emulator fixture run. */
    private void injectType111DecoderFaultForLab() {
        if (!type111FixtureMode || !isEmulator())
            throw new IllegalStateException("type111_decoder_fault_hook_outside_lab");
        throw new Api17SurfaceH264Decoder.DecodeException("lab_injected_type111_decoder_failure");
    }

    private void captureType111Proof(final String name) throws InterruptedException {
        final CountDownLatch saved = new CountDownLatch(1);
        main.post(new Runnable() { public void run() {
            saveBinderViewProof(name);
            saved.countDown();
        }});
        requireType111(awaitRace(saved), "decoded_type111_view_capture_saved");
    }

    private void closeType111Lab(final String reason) {
        final CountDownLatch closedLab = new CountDownLatch(1);
        main.post(new Runnable() { public void run() {
            stopOwnedDisplay(reason);
            closedLab.countDown();
        }});
        requireType111(awaitRace(closedLab), "type111_lab_teardown_completed");
    }

    private static void requireType111(boolean passed, String assertion) {
        if (!passed) throw new IllegalStateException("type111_" + assertion);
    }

    private static final class ExpectedType110SinkLoss extends RuntimeException {
        private static final long serialVersionUID = 1L;
        final long sessionId;
        ExpectedType110SinkLoss(long sessionId, Throwable cause) {
            super("type110_lab_sink_died", cause);
            this.sessionId = sessionId;
        }
    }

    private void submitNextSyntheticDiagnosticFrame(final long generation) {
        if (!active || closing || renderer == null || generation != activeGeneration ||
                syntheticDiagnosticSource == null) return;
        DecodedFrame frame = syntheticDiagnosticSource.nextFrame(generation);
        if (frame == null) {
            stopOwnedDisplay("diagnostic-video-source-ended");
            return;
        }
        submitDiagnosticFrame(frame, generation);
    }

    private void submitDiagnosticFrame(DecodedFrame frame, final long generation) {
        try {
            final long expectedTimestampNs = frame.presentationTimeNs;
            diagnosticFrameIndex++;
            log("DIAGNOSTIC_FRAME_SUBMITTED_TO_BINDER counter=" + diagnosticFrameIndex +
                    " generation=" + generation + " source=" + frame.width + "x" + frame.height +
                    " timestamp_ns=" + frame.presentationTimeNs + " bytes=" + frame.byteSize());
            FrameIpcClient client = frameIpcClient;
            if (client == null || !client.submit(frame, generation, new FrameIpcClient.Callback() {
                public void complete(final boolean accepted, final String reason) {
                    main.post(new Runnable() { public void run() {
                        if (!active || closing || activeGeneration != generation) return;
                        log("DIAGNOSTIC_BINDER_RESULT accepted=" + accepted + " reason=" + reason);
                        if (!accepted) stopOwnedDisplay("diagnostic-binder-rejected");
                        else awaitFrame(0, generation, expectedTimestampNs);
                    }});
                }
            })) stopOwnedDisplay("diagnostic-binder-not-started");
        } catch (RuntimeException failure) {
            stopOwnedDisplay("diagnostic-frame-submit-failed");
        }
    }

    private void closeDiagnosticSources() {
        if (staticDiagnosticSource != null) staticDiagnosticSource.close();
        if (syntheticDiagnosticSource != null) syntheticDiagnosticSource.close();
        staticDiagnosticSource = null;
        syntheticDiagnosticSource = null;
    }

    private void verifySyntheticGeometry(ClarityLinkContentView view) {
        RendererViewport fractional = new RendererViewport(
                new RendererViewport.Bounds(101, 61, 699, 419),
                java.util.Collections.singletonList(new RendererViewport.Bounds(300, 170, 500, 270)),
                RendererViewport.SYNTHETIC_TEST_ONLY);
        android.graphics.Rect safe = fractional.scaledSafeArea(401, 241);
        android.graphics.Rect protectedRect = fractional.scaled(
                new RendererViewport.Bounds(300, 170, 500, 270), 401, 241);
        if (safe.left != 51 || safe.top != 31 || safe.right != 350 || safe.bottom != 210 ||
                protectedRect.left != 150 || protectedRect.top != 85 ||
                protectedRect.right != 251 || protectedRect.bottom != 136)
            throw new IllegalStateException("fractional_viewport_rounding_failed");
        Bitmap snapshot = Bitmap.createBitmap(view.getWidth(), view.getHeight(), Bitmap.Config.ARGB_8888);
        try {
            view.draw(new Canvas(snapshot));
            int minX = view.getWidth(), minY = view.getHeight(), maxX = -1, maxY = -1;
            int red = 0, green = 0, blue = 0, yellow = 0;
            for (int y = 0; y < snapshot.getHeight(); y++) {
                for (int x = 0; x < snapshot.getWidth(); x++) {
                    int pixel = snapshot.getPixel(x, y);
                    int alpha = Color.alpha(pixel);
                    if (alpha == 0) continue;
                    if (x < 100 || x >= 700 || y < 60 || y >= 420 ||
                            (x >= 300 && x < 500 && y >= 170 && y < 270))
                        throw new IllegalStateException("synthetic_viewport_clip_failed");
                    minX = Math.min(minX, x); minY = Math.min(minY, y);
                    maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
                    int r = Color.red(pixel), g = Color.green(pixel), b = Color.blue(pixel);
                    if (r > 200 && g < 40 && b < 40) red++;
                    if (g > 200 && r < 40 && b < 40) green++;
                    if (b > 200 && r < 40 && g < 40) blue++;
                    if (r > 200 && g > 200 && b < 40) yellow++;
                }
            }
            if (maxX < minX || maxY < minY || maxX - minX + 1 < 170 || maxX - minX + 1 > 190 ||
                    maxY - minY + 1 < 350 || maxY - minY + 1 > 370 || red < 100 || green < 100 ||
                    blue != 0 || yellow != 0)
                throw new IllegalStateException("synthetic_crop_rotation_aspect_ratio_failed");
        } finally {
            snapshot.recycle();
        }
    }

    private boolean hasVisiblePixels(ClarityLinkContentView view) {
        Bitmap snapshot = Bitmap.createBitmap(view.getWidth(), view.getHeight(), Bitmap.Config.ARGB_8888);
        try {
            view.draw(new Canvas(snapshot));
            for (int y = 0; y < snapshot.getHeight(); y++)
                for (int x = 0; x < snapshot.getWidth(); x++)
                    if (Color.alpha(snapshot.getPixel(x, y)) != 0) return true;
            return false;
        } finally {
            snapshot.recycle();
        }
    }

    private void submitSyntheticFrame(final long generation) {
        FrameIpcClient client = frameIpcClient;
        if (client == null || renderer == null || ipcSubmitted) return;
        ipcSubmitted = true;
        FrameStreamIdentity streamIdentity = client.streamIdentity();
        final long streamGeneration = streamIdentity == null ? -1L : streamIdentity.streamGeneration;
        boolean started = client.submit(syntheticFrame(), streamGeneration, new FrameIpcClient.Callback() {
            public void complete(final boolean accepted, final String reason) {
                main.post(new Runnable() {
                    public void run() {
                        if (!active || closing || activeGeneration != generation) return;
                        if (!accepted) {
                            log("IPC_SYNTHETIC_FRAME_REJECTED generation=" + streamGeneration + " reason=" + reason);
                            stopOwnedDisplay("ipc-frame-rejected");
                            return;
                        }
                        log("IPC_SYNTHETIC_FRAME_ACCEPTED_BY_REMOTE_AND_VIEW_SINK generation=" + streamGeneration
                                + " timestamp=1 bytes=16 backpressure=single_in_flight");
                        if (crashAfterFirstFrame)
                            log("CRASH_PROBE_ARMED_AFTER_CL_R1_AND_FRAME_SEQUENCE");
                    }
                });
            }
        });
        if (!started) log("IPC_FRAME_BACKPRESSURE_REJECT generation=" + streamGeneration);
    }

    private void saveBinderViewProof() {
        saveBinderViewProof("test6a-binder-view-proof.png");
    }

    private void saveBinderViewProof(String fileName) {
        final FrameLayout root = presentationRoot;
        if (root == null || root.getWidth() <= 0 || root.getHeight() <= 0) {
            log("BINDER_VIEW_PROOF_SKIPPED reason=root_not_measured");
            return;
        }
        Bitmap proof = Bitmap.createBitmap(root.getWidth(), root.getHeight(), Bitmap.Config.ARGB_8888);
        FileOutputStream output = null;
        try {
            root.draw(new Canvas(proof));
            File file = new File(getFilesDir(), fileName);
            output = new FileOutputStream(file);
            if (!proof.compress(Bitmap.CompressFormat.PNG, 100, output))
                throw new java.io.IOException("PNG encoding failed");
            output.flush();
            log("BINDER_VIEW_PROOF_SAVED path=" + file.getName() + " width=" +
                    proof.getWidth() + " height=" + proof.getHeight() + " renderer_view=" +
                    (renderer != null && renderer.contentView() != null));
        } catch (Exception failure) {
            log("BINDER_VIEW_PROOF_FAILED type=" + failure.getClass().getSimpleName());
        } finally {
            if (output != null) try { output.close(); } catch (Exception ignored) { }
            if (!proof.isRecycled()) proof.recycle();
        }
    }

    private DecodedFrame syntheticFrame() { return syntheticFrame(1L); }

    private DecodedFrame syntheticFrame(long timestampNs) {
        byte[] rgba = new byte[] {
                (byte) 255, 0, 0, (byte) 255, 0, (byte) 255, 0, (byte) 255,
                0, 0, (byte) 255, (byte) 255, (byte) 255, (byte) 255, 0, (byte) 255
        };
        return new DecodedFrame(2, 2, 8, timestampNs, 90, 0, 0, 2, 1, ByteBuffer.wrap(rgba));
    }

    private void releaseRenderer() {
        Display1OutputBackend old = renderer;
        renderer = null;
        presentationRoot = null;
        if (old != null) {
            try { old.close(); }
            catch (RuntimeException failure) { log("RENDERER_CLOSE_FAILED type=" + failure.getClass().getSimpleName()); }
            log("RENDERER_RELEASED");
        }
    }

    private void stopOwnedDisplay(String reason) {
        if (closing) return;
        closing = true;
        active = false;
        FixtureRunToken runToken = type111FixtureRunToken;
        if (runToken != null) runToken.cancelForDetach();
        type111RunStarted = false;
        Thread fixtureWorker = type111FixtureWorker;
        if (fixtureWorker != null && fixtureWorker != Thread.currentThread() &&
                !"type110-lab-sink-disconnected".equals(reason)) fixtureWorker.interrupt();
        log("LIFECYCLE_STOP reason=" + reason);
        closeDiagnosticSources();
        releaseRenderer();
        SecondaryDisplayHost old = displayHost;
        displayHost = null;
        if (old != null) {
            boolean dismissed = false;
            try { old.close(); dismissed = true; }
            catch (RuntimeException failure) { log("PRESENTATION_CLOSE_FAILED type=" + failure.getClass().getSimpleName()); }
            if (dismissed) log("PRESENTATION_DISMISS_REQUESTED reason=" + reason);
        }
        borrowedPresentationSurface = null;
        closeIpcSession();
        activeGeneration = 0L;
        closing = false;
    }

    /** Release only the Activity-owned View attachment while retaining the Type110 parent session. */
    private void closeViewAttachmentPreservingParent(String reason) {
        if (closing || (!active && displayHost == null && renderer == null)) return;
        closing = true;
        active = false;
        FixtureRunToken runToken = type111FixtureRunToken;
        if (runToken != null) runToken.cancelForDetach();
        type111RunStarted = false;
        Thread fixtureWorker = type111FixtureWorker;
        if (fixtureWorker != null) fixtureWorker.interrupt();
        log("VIEW_ATTACHMENT_DETACH reason=" + reason + " parent_session_preserved=true");
        closeDiagnosticSources();
        releaseRenderer();
        SecondaryDisplayHost old = displayHost;
        displayHost = null;
        if (old != null) {
            try { old.close(); }
            catch (RuntimeException failure) {
                log("PRESENTATION_CLOSE_FAILED type=" + failure.getClass().getSimpleName());
            }
        }
        borrowedPresentationSurface = null;
        FrameIpcClient type111Client = frameIpcClient;
        FrameIpcClient type110Client = primaryLabIpcClient;
        FrameStreamIdentity owner = type110Client == null ? null : type110Client.streamIdentity();
        FrameStreamIdentity child = type111Client == null ? null : type111Client.streamIdentity();
        Type111ControlClient control = type111ControlClient;
        if (!parentOwnerLost && control != null && owner != null && child != null) {
            try {
                boolean detached = control.detachType111Sink(owner, child);
                log("TYPE111_LIFECYCLE_DETACH accepted=" + detached +
                        " session_id=" + child.sessionId + " generation=" +
                        child.streamGeneration + " parent_session_preserved=true");
            } catch (Exception failure) {
                log("TYPE111_LIFECYCLE_DETACH_FAILED type=" +
                        failure.getClass().getSimpleName());
            }
        } else if (parentOwnerLost) {
            log("TYPE111_LIFECYCLE_DETACH_SKIPPED reason=parent-owner-lost stale_session_rpc=false");
        }
        frameIpcClient = null;
        primaryLabIpcClient = null;
        type111ControlClient = null;
        ipcSessionReady = false;
        ipcSessionStartAttempted = false;
        compositorEndpoint = null;
        primaryLabSinkBinder = null;
        type110SinkStartAttempted = false;
        if (child != null) viewSink.close(child.streamGeneration);
        if (primarySinkBound) {
            try { unbindService(primarySinkConnection); } catch (IllegalArgumentException ignored) { }
            primarySinkBound = false;
        }
        if (compositorBound) {
            try { unbindService(compositorConnection); } catch (IllegalArgumentException ignored) { }
            compositorBound = false;
        }
        reattachSessionId = activeGeneration;
        parentSessionPreservedForLifecycle = true;
        lifecycleReattachPending = true;
        ipcSubmitted = false;
        closing = false;
    }

    private void closeIpcSession() {
        releaseSecurityTestProducerService(activeGeneration);
        FrameIpcClient client = frameIpcClient;
        FrameIpcClient primaryClient = primaryLabIpcClient;
        frameIpcClient = null;
        primaryLabIpcClient = null;
        ipcSessionReady = false;
        Type111ControlClient control = type111ControlClient;
        type111ControlClient = null;
        FrameStreamIdentity type110Owner = primaryClient == null ? null : primaryClient.streamIdentity();
        boolean ownerLost = parentOwnerLost;
        if (!ownerLost && control != null && type110Owner != null) {
            try { control.parentTeardown(type110Owner); }
            catch (Exception failure) { log("TYPE111_PARENT_TEARDOWN_FAILED type=" +
                    failure.getClass().getSimpleName()); }
        }
        if (!ownerLost && client != null) client.end(activeGeneration);
        if (!ownerLost && primaryClient != null) primaryClient.end(activeGeneration);
        if (ownerLost)
            log("CL_R4B_ACTIVITY_OWNER_CLEANUP_PASS session_id=" + activeGeneration +
                    " parent_teardown_request_skipped=true stale_stream_end_skipped=true " +
                    "detached_owner_loss=" + parentOwnerLossWhileDetached);
        if (compositorDeathRecipient != null && observedCompositorBinder != null) {
            try { observedCompositorBinder.unlinkToDeath(compositorDeathRecipient, 0); }
            catch (RuntimeException ignored) { }
        }
        compositorDeathRecipient = null;
        observedCompositorBinder = null;
        primaryLabSinkBinder = null;
        viewSink.close(activeGeneration);
        if (primarySinkBound) {
            try { unbindService(primarySinkConnection); }
            catch (IllegalArgumentException ignored) { }
            primarySinkBound = false;
        }
        if (compositorBound) {
            try { unbindService(compositorConnection); }
            catch (IllegalArgumentException ignored) { }
            compositorBound = false;
        }
        if (type110SinkServiceStarted) {
            stopService(new Intent(this, FrameLabSinkService.class));
            type110SinkServiceStarted = false;
        }
        if (compositorServiceStarted) {
            stopService(new Intent(this, CompositorService.class));
            compositorServiceStarted = false;
        }
        compositorEndpoint = null;
        parentOwnerLossSessionId = 0L;
        parentOwnerLossWhileDetached = false;
        parentOwnerLost = false;
    }

    @Override protected void onPause() {
        if (active || displayHost != null) closeViewAttachmentPreservingParent("activity-pause");
        super.onPause();
    }

    @Override protected void onDestroy() {
        if (active || displayHost != null || renderer != null)
            closeViewAttachmentPreservingParent("activity-destroy");
        super.onDestroy();
    }

    @Override protected void onResume() {
        super.onResume();
        if (parentSessionPreservedForLifecycle && reattachSessionId > 0L) {
            if (parentOwnerLost && parentOwnerLossSessionId == reattachSessionId) {
                log("CL_R4B_ACTIVITY_OWNER_REATTACH_ABORTED session_id=" + reattachSessionId +
                        " stale_session_rpc=false fresh_session_required=true");
                parentSessionPreservedForLifecycle = false;
                lifecycleReattachPending = false;
                reattachSessionId = 0L;
                stopOwnedDisplay("parent-owner-died-during-detach");
                return;
            }
            parentSessionPreservedForLifecycle = false;
            log("VIEW_ATTACHMENT_REATTACH_REQUEST session_id=" + reattachSessionId +
                    " parent_session_preserved=true");
            startEmulatorLab();
        }
    }

    @Override protected void onSaveInstanceState(Bundle state) {
        // Deliberately do not persist lab admission or replay a Presentation after process recovery.
        super.onSaveInstanceState(state);
    }

    @Override protected void onNewIntent(android.content.Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        if (isExplicitLabRequest(intent.getExtras())) startEmulatorLab();
    }

    private static void log(String message) { Log.i(TAG, message); }
}
