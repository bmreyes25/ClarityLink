package org.claritylink.android;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Message;
import android.os.Messenger;
import android.os.ParcelFileDescriptor;
import android.os.RemoteException;
import android.util.Base64;
import android.util.Log;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

import org.claritylink.renderer.DecodedFrame;
import org.claritylink.renderer.Display1OutputBackend;
import org.claritylink.renderer.HondaStyleSimulatorRendererHost;

import org.claritylink.android.HondaStyleDisplayHostSimulator;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayDeque;
import java.util.Arrays;

/** Offline API17 proof that decoder output can cross a bounded Messenger/MemoryFile/PFD path. */
public final class MessengerFrameLabActivity extends Activity {
    private static final String TAG = "ClarityLinkMessengerLab";
    private final Handler ui = new Handler();
    private final ArrayDeque<DecodedFrame> waiting = new ArrayDeque<DecodedFrame>();
    private Messenger remote;
    private Messenger replies;
    private HondaStyleDisplayHostSimulator simulator;
    private Display1OutputBackend renderer;
    private TextView status;
    private long generation;
    private long nextSequence = 1L;
    private boolean navigation = true;
    private boolean interrupted;
    private boolean bound;
    private boolean inFlight;
    private boolean scenarioEnabled;
    private boolean scenarioCrashPending;
    private boolean scenarioExpectedStale;
    private boolean scenarioStaleRejected;
    private boolean scenarioNavigationRejected;
    private boolean scenarioInterruptRejected;
    private DecodedFrame activeFrame;
    private DecodedFrame lastAcceptedFrame;
    private long lastAcceptedGeneration;
    private long lastAcceptedSequence;
    private int sent;
    private int accepted;
    private int rejected;
    private int maxQueued;

    private final ServiceConnection connection = new ServiceConnection() {
        public void onServiceConnected(ComponentName name, IBinder binder) {
            remote = new Messenger(binder);
            generation = Math.max(generation + 1L, System.nanoTime());
            nextSequence = 1L;
            inFlight = false;
            activeFrame = null;
            waiting.clear();
            sendControl(MessengerFrameHostService.ATTACH, 0, "host_attached");
            updateStatus("simulated host connected; generation=" + generation);
            if (scenarioEnabled) ui.postDelayed(new Runnable() {
                public void run() { decodeAndQueueFixture(); }
            }, scenarioCrashPending ? 600L : 1000L);
            scenarioCrashPending = false;
        }
        public void onServiceDisconnected(ComponentName name) {
            remote = null;
            inFlight = false;
            activeFrame = null;
            waiting.clear();
            closeRenderer();
            generation++;
            updateStatus("simulated host process ended; local content detached");
            if (scenarioEnabled) Log.i(TAG, "SCENARIO_SIMULATED_HOST_PROCESS_DIED");
        }
    };

    private final android.os.Handler responseHandler = new android.os.Handler() {
        @Override public void handleMessage(Message message) {
            if (message.what != MessengerFrameHostService.ACK) return;
            onReply(message);
        }
    };

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        simulator = new HondaStyleDisplayHostSimulator(this);
        replies = new Messenger(responseHandler);
        scenarioEnabled = getIntent() != null && getIntent().getBooleanExtra("run_cl_r12_scenario", false);
        buildUi();
        Intent intent = new Intent(this, MessengerFrameHostService.class);
        bound = bindService(intent, connection, Context.BIND_AUTO_CREATE);
        if (!bound) updateStatus("service bind failed");
    }

    private void buildUi() {
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setBackgroundColor(Color.rgb(15, 24, 38));
        panel.setPadding(12, 8, 12, 8);
        status = new TextView(this);
        status.setTextColor(Color.WHITE);
        status.setText("Offline display laboratory; no Honda or vehicle services");
        panel.addView(status, new LinearLayout.LayoutParams(-1, 72));
        addButton(panel, "Decode + submit synthetic Type111 H.264", new Runnable() {
            public void run() { decodeAndQueueFixture(); }
        });
        addButton(panel, "Toggle Navigation page", new Runnable() {
            public void run() { setNavigation(!navigation); }
        });
        addButton(panel, "Toggle interrupt container", new Runnable() {
            public void run() { setInterrupt(!interrupted); }
        });
        addButton(panel, "Crash + recover simulated host process", new Runnable() {
            public void run() { crashSimulatedHost(); }
        });
        LinearLayout outer = new LinearLayout(this);
        outer.setOrientation(LinearLayout.VERTICAL);
        outer.addView(panel, new LinearLayout.LayoutParams(-1, -2));
        outer.addView(simulator.getDisplayRoot(), new LinearLayout.LayoutParams(-1, 0, 1));
        setContentView(outer);
    }

    private void addButton(LinearLayout parent, String label, final Runnable action) {
        Button button = new Button(this);
        button.setText(label);
        button.setOnClickListener(new android.view.View.OnClickListener() {
            public void onClick(android.view.View view) { action.run(); }
        });
        parent.addView(button, new LinearLayout.LayoutParams(-1, -2));
    }

    private void decodeAndQueueFixture() {
        if (remote == null || !waiting.isEmpty() || inFlight) {
            updateStatus("submit rejected by missing host or single-flight backpressure gate");
            return;
        }
        new Thread(new Runnable() {
            public void run() {
                Api17BufferH264Decoder decoder = null;
                try {
                    byte[] fixture = Base64.decode(readAsset("type111-blue-32x32.h264.b64"), Base64.DEFAULT);
                    byte[] config = Api17SurfaceH264Decoder.extractCodecConfig(fixture);
                    byte[][] accessUnits = Api17SurfaceH264Decoder.extractVclFrames(fixture);
                    if (accessUnits.length < 2) throw new IOException("type111_fixture_needs_two_frames");
                    final long decoderGeneration = generation;
                    long basePtsUs = System.nanoTime() / 1000L;
                    decoder = new Api17BufferH264Decoder(32, 32, decoderGeneration, config);
                    DecodedFrame first = decoder.decode(accessUnits[0], basePtsUs, decoderGeneration, 3000L);
                    DecodedFrame second = decoder.decode(accessUnits[1], basePtsUs + 100000L,
                            decoderGeneration, 3000L);
                    final ArrayDeque<DecodedFrame> decoded = new ArrayDeque<DecodedFrame>();
                    if (first != null) decoded.add(first);
                    if (second != null) decoded.add(second);
                    ui.post(new Runnable() {
                        public void run() {
                            if (generation != decoderGeneration) return;
                            while (!decoded.isEmpty() && waiting.size() < 2) waiting.add(decoded.remove());
                            maxQueued = Math.max(maxQueued, waiting.size());
                            sendNext();
                        }
                    });
                } catch (Throwable failure) {
                    Log.e(TAG, "TYPE111_FIXTURE_DECODE_FAILED", failure);
                    ui.post(new Runnable() { public void run() { updateStatus("decoder fixture failed; see emulator log"); } });
                } finally { if (decoder != null) decoder.close(); }
            }
        }, "ClarityLinkSyntheticType111Decoder").start();
    }

    private byte[] readAsset(String name) throws IOException {
        InputStream input = getAssets().open(name);
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] chunk = new byte[1024];
        int count;
        try {
            while ((count = input.read(chunk)) != -1) {
                if (output.size() + count > 16384) throw new IOException("fixture_size_limit");
                output.write(chunk, 0, count);
            }
        } finally { input.close(); }
        return output.toByteArray();
    }

    private void sendNext() {
        if (remote == null || inFlight || waiting.isEmpty()) return;
        final DecodedFrame frame = waiting.remove();
        ParcelFileDescriptor descriptor = null;
        try {
            byte[] rgba = MessengerFrameParcel.rgba(frame);
            descriptor = MessengerFrameParcel.write(rgba);
            Bundle data = frameMetadata(frame, rgba.length, generation, nextSequence++);
            sendFrame(frame, generation, data.getLong(MessengerFrameHostService.KEY_SEQUENCE),
                    descriptor, data);
        } catch (Exception failure) {
            rejected++;
            updateStatus("frame transport failed: " + failure.getClass().getSimpleName());
        } finally {
            if (descriptor != null) try { descriptor.close(); } catch (IOException ignored) { }
        }
    }

    private void sendFrame(DecodedFrame frame, long frameGeneration, long sequence,
            ParcelFileDescriptor descriptor, Bundle metadata) throws RemoteException {
        if (remote == null || inFlight) { close(descriptor); return; }
        Message request = Message.obtain(null, MessengerFrameHostService.FRAME);
        request.replyTo = replies;
        metadata.putLong(MessengerFrameHostService.KEY_GENERATION, frameGeneration);
        metadata.putLong(MessengerFrameHostService.KEY_SEQUENCE, sequence);
        metadata.putParcelable(MessengerFrameHostService.KEY_PFD, descriptor);
        request.setData(metadata);
        remote.send(request);
        activeFrame = frame;
        inFlight = true;
        sent++;
        updateStatus("frame sent; waiting for host receipt (single-flight backpressure)");
    }

    private Bundle frameMetadata(DecodedFrame frame, int bytes, long frameGeneration, long sequence) {
        Bundle data = new Bundle();
        data.putInt(MessengerFrameHostService.KEY_WIDTH, frame.width);
        data.putInt(MessengerFrameHostService.KEY_HEIGHT, frame.height);
        data.putInt(MessengerFrameHostService.KEY_STRIDE, frame.rowStride);
        data.putLong(MessengerFrameHostService.KEY_PTS, frame.presentationTimeNs);
        data.putInt(MessengerFrameHostService.KEY_ROTATION, frame.rotationDegrees);
        data.putInt(MessengerFrameHostService.KEY_CROP_LEFT, frame.cropLeft);
        data.putInt(MessengerFrameHostService.KEY_CROP_TOP, frame.cropTop);
        data.putInt(MessengerFrameHostService.KEY_CROP_RIGHT, frame.cropRight);
        data.putInt(MessengerFrameHostService.KEY_CROP_BOTTOM, frame.cropBottom);
        data.putInt(MessengerFrameHostService.KEY_BYTES, bytes);
        data.putLong(MessengerFrameHostService.KEY_GENERATION, frameGeneration);
        data.putLong(MessengerFrameHostService.KEY_SEQUENCE, sequence);
        return data;
    }

    private void onReply(Message response) {
        if (response.arg1 != MessengerFrameHostService.FRAME) return;
        Bundle data = response.getData();
        if (data.getLong(MessengerFrameHostService.KEY_GENERATION, -1L) != generation) {
            close(data.<ParcelFileDescriptor>getParcelable(MessengerFrameHostService.KEY_PFD));
            rejected++;
            inFlight = false;
            activeFrame = null;
            waiting.clear();
            if (scenarioEnabled && scenarioExpectedStale) {
                scenarioExpectedStale = false;
                scenarioStaleRejected = true;
                Log.i(TAG, "SCENARIO_STALE_GENERATION_REJECTED");
                ui.postDelayed(new Runnable() {
                    public void run() {
                        setNavigation(false);
                        ui.postDelayed(new Runnable() {
                            public void run() { decodeAndQueueFixture(); }
                        }, 350L);
                    }
                }, 350L);
            }
            updateStatus("stale host reply rejected");
            return;
        }
        if (!data.getBoolean(MessengerFrameHostService.KEY_ACCEPTED)) {
            close(data.<ParcelFileDescriptor>getParcelable(MessengerFrameHostService.KEY_PFD));
            inFlight = false;
            activeFrame = null;
            rejected++;
            waiting.clear();
            final String reason = data.getString(MessengerFrameHostService.KEY_REASON);
            updateStatus("host rejected frame: " + reason);
            if (scenarioEnabled && "navigation_inactive".equals(reason)) {
                scenarioNavigationRejected = true;
                ui.postDelayed(new Runnable() {
                    public void run() {
                        setNavigation(true);
                        ui.postDelayed(new Runnable() {
                            public void run() {
                                setInterrupt(true);
                                ui.postDelayed(new Runnable() {
                                    public void run() { decodeAndQueueFixture(); }
                                }, 350L);
                            }
                        }, 350L);
                    }
                }, 350L);
            } else if (scenarioEnabled && "interrupt_preemption".equals(reason)) {
                scenarioInterruptRejected = true;
                ui.postDelayed(new Runnable() {
                    public void run() {
                        setInterrupt(false);
                        ui.postDelayed(new Runnable() {
                            public void run() { decodeAndQueueFixture(); }
                        }, 350L);
                    }
                }, 350L);
            }
            return;
        }
        ParcelFileDescriptor descriptor = data.getParcelable(MessengerFrameHostService.KEY_PFD);
        int bytes = data.getInt(MessengerFrameHostService.KEY_BYTES);
        try {
            byte[] rgba = MessengerFrameParcel.read(descriptor, bytes);
            if (activeFrame == null || !Arrays.equals(MessengerFrameParcel.rgba(activeFrame), rgba))
                throw new IOException("round_trip_pixel_mismatch");
            DecodedFrame frame = MessengerFrameParcel.decoded(
                    data.getInt(MessengerFrameHostService.KEY_WIDTH),
                    data.getInt(MessengerFrameHostService.KEY_HEIGHT),
                    data.getInt(MessengerFrameHostService.KEY_STRIDE),
                    data.getLong(MessengerFrameHostService.KEY_PTS),
                    data.getInt(MessengerFrameHostService.KEY_ROTATION),
                    data.getInt(MessengerFrameHostService.KEY_CROP_LEFT),
                    data.getInt(MessengerFrameHostService.KEY_CROP_TOP),
                    data.getInt(MessengerFrameHostService.KEY_CROP_RIGHT),
                    data.getInt(MessengerFrameHostService.KEY_CROP_BOTTOM), rgba);
            if (!navigation || interrupted) throw new IOException("host_page_changed_before_render");
            if (renderer == null) {
                renderer = new Display1OutputBackend(new HondaStyleSimulatorRendererHost(simulator),
                        new Display1OutputBackend.Viewport(0, 0, 800, 480), generation);
                renderer.attach();
            }
            renderer.submit(frame);
            accepted++;
            lastAcceptedFrame = frame;
            lastAcceptedGeneration = data.getLong(MessengerFrameHostService.KEY_GENERATION);
            lastAcceptedSequence = data.getLong(MessengerFrameHostService.KEY_SEQUENCE);
            inFlight = false;
            activeFrame = null;
            updateStatus("rendered Type111 fixture frames=" + accepted + " · pixel bytes round-tripped exactly" +
                    " · max queued=" + maxQueued + " · transfer transactions in flight ≤1");
            if (scenarioEnabled) advanceScenarioAfterAccepted();
            sendNext();
        } catch (Exception failure) {
            rejected++;
            inFlight = false;
            activeFrame = null;
            updateStatus("frame reconstruction/render failed: " + failure.getMessage());
        }
    }

    private void advanceScenarioAfterAccepted() {
        if (accepted == 1) {
            scenarioExpectedStale = true;
            long staleGeneration = lastAcceptedGeneration;
            long staleSequence = lastAcceptedSequence;
            setNavigation(false);
            setNavigation(true);
            final long requestedGeneration = staleGeneration;
            final long requestedSequence = staleSequence;
            ui.postDelayed(new Runnable() {
                public void run() { sendStaleGenerationProbe(requestedGeneration, requestedSequence); }
            }, 500L);
        } else if (accepted == 2) {
            scenarioCrashPending = true;
            crashSimulatedHost();
        } else if (accepted == 3 && scenarioStaleRejected && scenarioNavigationRejected &&
                scenarioInterruptRejected) {
            scenarioEnabled = false;
            Log.i(TAG, "CL_R12_MESSENGER_LAB_PASS type111_decoder=true memoryfile_pfd_messenger=true" +
                    " pixel_identity=true stale_generation_rejected=true navigation_withdrawal=true" +
                    " interrupt_preemption=true producer_host_process_recovery=true type110_untouched=true");
            updateStatus("CL-R12 offline integration scenario PASS; Type110 path untouched");
            ui.postDelayed(new Runnable() { public void run() { finish(); } }, 1000L);
        }
    }

    private void sendStaleGenerationProbe(long staleGeneration, long staleSequence) {
        if (remote == null || inFlight || lastAcceptedFrame == null) return;
        ParcelFileDescriptor descriptor = null;
        try {
            byte[] rgba = MessengerFrameParcel.rgba(lastAcceptedFrame);
            descriptor = MessengerFrameParcel.write(rgba);
            Bundle metadata = frameMetadata(lastAcceptedFrame, rgba.length, staleGeneration, staleSequence);
            sendFrame(lastAcceptedFrame, staleGeneration, staleSequence, descriptor, metadata);
        } catch (Exception failure) {
            scenarioExpectedStale = false;
            Log.e(TAG, "SCENARIO_STALE_PROBE_FAILED", failure);
        } finally {
            close(descriptor);
        }
    }

    private void setNavigation(boolean active) {
        navigation = active;
        if (!active) {
            waiting.clear();
            closeRenderer();
            simulator.setNavigationActive(false);
        } else {
            simulator.setNavigationActive(true);
            generation++;
            sendControl(MessengerFrameHostService.ATTACH, 0, "navigation_reselected");
        }
        sendControl(MessengerFrameHostService.PAGE, active ? 1 : 0, "navigation_page");
        updateStatus("Navigation " + (active ? "selected" : "deselected") + "; stale content cleared");
    }

    private void setInterrupt(boolean active) {
        interrupted = active;
        simulator.setSimulatedStockWarningVisible(active);
        sendControl(MessengerFrameHostService.INTERRUPT, active ? 1 : 0, "interrupt_state");
        if (active) waiting.clear(); else sendNext();
        updateStatus("simulated interrupt " + (active ? "preempts" : "released") + " Navigation content");
    }

    private void crashSimulatedHost() {
        if (remote == null) return;
        closeRenderer();
        waiting.clear();
        sendControl(MessengerFrameHostService.CRASH_FIXTURE, 0, "crash_fixture");
        updateStatus("requested process death in emulator-only simulated host");
    }

    private void sendControl(int what, int value, String reason) {
        if (remote == null) return;
        Message message = Message.obtain(null, what);
        message.arg1 = value;
        message.replyTo = replies;
        Bundle data = new Bundle();
        data.putLong(MessengerFrameHostService.KEY_GENERATION, generation);
        data.putString("reason", reason);
        message.setData(data);
        try { remote.send(message); }
        catch (RemoteException failure) { Log.w(TAG, "control_send_failed " + reason, failure); }
    }

    private void closeRenderer() {
        if (renderer != null) {
            try { renderer.close(); } catch (RuntimeException failure) {
                Log.w(TAG, "simulated_renderer_detach_failed", failure);
            }
            renderer = null;
        }
    }

    private void updateStatus(final String text) {
        if (status == null) return;
        final String full = text + "\n sent=" + sent + " accepted=" + accepted +
                " rejected=" + rejected + " generation=" + generation;
        if (android.os.Looper.myLooper() == android.os.Looper.getMainLooper()) status.setText(full);
        else ui.post(new Runnable() { public void run() { if (status != null) status.setText(full); } });
        Log.i(TAG, "LAB_STATUS " + text + " sent=" + sent + " accepted=" + accepted +
                " rejected=" + rejected + " generation=" + generation);
    }

    private static void close(ParcelFileDescriptor descriptor) {
        if (descriptor != null) try { descriptor.close(); } catch (IOException ignored) { }
    }

    @Override protected void onDestroy() {
        sendControl(MessengerFrameHostService.DETACH, 0, "activity_destroyed");
        closeRenderer();
        waiting.clear();
        if (bound) { unbindService(connection); bound = false; }
        if (simulator != null && !simulator.isClosed()) simulator.close();
        super.onDestroy();
    }
}
