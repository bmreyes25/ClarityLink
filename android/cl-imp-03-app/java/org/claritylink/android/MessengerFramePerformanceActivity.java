package org.claritylink.android;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Debug;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.IBinder;
import android.os.Message;
import android.os.Messenger;
import android.os.ParcelFileDescriptor;
import android.os.RemoteException;
import android.util.Log;
import android.widget.FrameLayout;
import android.widget.TextView;

import org.claritylink.renderer.DecodedFrame;
import org.claritylink.renderer.Display1OutputBackend;
import org.claritylink.renderer.HondaStyleSimulatorRendererHost;

import java.io.File;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.util.Arrays;

/** Timed, synthetic 800x480 MemoryFile/PFD/Messenger regression and soak harness. */
public final class MessengerFramePerformanceActivity extends Activity {
    private static final String TAG = "ClarityLinkR12B";
    private static final int WIDTH = 800;
    private static final int HEIGHT = 480;
    private static final int STRIDE = WIDTH * 4;
    private static final int FRAME_BYTES = STRIDE * HEIGHT;
    private static final long FRAME_INTERVAL_NS = 1000000000L / 30L;
    private static final long SHORT_RUN_NS = 30L * 1000000000L;
    private static final long SOAK_RUN_NS = 600L * 1000000000L;
    private static final int MAX_SAMPLES = 20000;

    private final Handler ui = new Handler();
    private HandlerThread schedulerThread;
    private HandlerThread senderThread;
    private Handler scheduler;
    private Handler sender;
    private final long[] latencyNs = new long[MAX_SAMPLES];
    private volatile Messenger remote;
    private Messenger replies;
    private HondaStyleDisplayHostSimulator simulator;
    private Display1OutputBackend renderer;
    private TextView status;
    private String mode;
    private volatile long generation;
    private long sequence;
    private volatile long runStartNs;
    private volatile long runEndNs;
    private long nextDueNs;
    private volatile long sentAtNs;
    private long lastProgressNs;
    private boolean bound;
    private volatile boolean running;
    private volatile boolean inFlight;
    private volatile boolean finishPending;
    private volatile DecodedFrame activeFrame;
    private volatile int offered;
    private volatile int sent;
    private volatile int hostAccepted;
    private volatile int delivered;
    private volatile int dropBackpressure;
    private volatile int hostRejected;
    private volatile int transportErrors;
    private volatile int pixelMismatches;
    private volatile int maxInFlight;
    private volatile int latencyCount;
    private int producerFdBaseline = -1;
    private int producerFdFinal = -1;
    private long producerJavaBaseline;
    private long producerJavaFinal;
    private long producerNativeBaseline;
    private long producerNativeFinal;
    private int hostPidBaseline = -1;
    private int hostFdBaseline = -1;
    private int hostFdFinal = -1;
    private long hostJavaBaseline;
    private long hostJavaFinal;
    private long hostNativeBaseline;
    private long hostNativeFinal;
    private long hostMemoryFilesCreated;
    private long hostMemoryFilesClosed;
    private long hostMemoryFilesOpen;
    private long producerMemoryFilesCreated;
    private long producerMemoryFilesClosed;
    private long producerMemoryFilesOpen;
    private long hostReads;
    private long hostReadBytes;
    private long lastProgressDelivered;
    private long lastProgressNsValue;
    private boolean finalStatsReceived;
    private boolean partialFrameRejected;
    private int preflightStage;

    private final Runnable frameTick = new Runnable() {
        public void run() { offerTick(); }
    };
    private final Runnable finishStats = new Runnable() {
        public void run() { requestFinalStats(); }
    };

    private final ServiceConnection connection = new ServiceConnection() {
        public void onServiceConnected(ComponentName name, IBinder binder) {
            remote = new Messenger(binder);
            generation = Math.max(generation + 1L, System.nanoTime());
            sequence = 0L;
            sendControl(MessengerFrameHostService.ATTACH, "benchmark_attach");
            Log.i(TAG, "R12B_HOST_CONNECTED pid_from_ack_pending=true generation=" + generation);
            ui.postDelayed(new Runnable() {
                public void run() { requestBaselineStats(); }
            }, 500L);
        }

        public void onServiceDisconnected(ComponentName name) {
            remote = null;
            if (inFlight) {
                inFlight = false;
                activeFrame = null;
                transportErrors++;
            }
            Log.e(TAG, "R12B_UNEXPECTED_IPC_CLOSED mode=" + mode + " delivered=" + delivered);
            if (running) finishWithError("unexpected_ipc_closure");
        }
    };

    private final android.os.Handler replyHandler = new android.os.Handler() {
        @Override public void handleMessage(Message message) {
            if (message.what == MessengerFrameHostService.ACK) onReply(message);
        }
    };

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        schedulerThread = new HandlerThread("ClarityLinkR12BScheduler");
        senderThread = new HandlerThread("ClarityLinkR12BSender");
        schedulerThread.start();
        senderThread.start();
        scheduler = new Handler(schedulerThread.getLooper());
        sender = new Handler(senderThread.getLooper());
        mode = getIntent() == null ? "" : getIntent().getStringExtra("cl_r12b_mode");
        if (!"short".equals(mode) && !"soak".equals(mode)) {
            finishWithError("invalid_mode");
            return;
        }
        simulator = new HondaStyleDisplayHostSimulator(this);
        replies = new Messenger(replyHandler);
        FrameLayout root = simulator.getDisplayRoot();
        status = new TextView(this);
        status.setTextColor(Color.WHITE);
        status.setBackgroundColor(Color.rgb(15, 24, 38));
        status.setText("Synthetic API17 Messenger performance run: " + mode);
        root.addView(status, new FrameLayout.LayoutParams(-1, 42));
        setContentView(root);
        Intent service = new Intent(this, MessengerFrameHostService.class);
        bound = bindService(service, connection, Context.BIND_AUTO_CREATE);
        if (!bound) finishWithError("service_bind_failed");
    }

    private void requestBaselineStats() {
        if (remote == null || running) return;
        producerFdBaseline = fdCount();
        Runtime runtime = Runtime.getRuntime();
        producerJavaBaseline = runtime.totalMemory() - runtime.freeMemory();
        producerNativeBaseline = Debug.getNativeHeapAllocatedSize();
        sendControl(MessengerFrameHostService.STATS, "baseline_stats");
    }

    private void startRun() {
        if (remote == null || running) return;
        running = true;
        offered = sent = hostAccepted = delivered = dropBackpressure = hostRejected = 0;
        transportErrors = pixelMismatches = maxInFlight = latencyCount = 0;
        sequence = 0L;
        long duration = "short".equals(mode) ? SHORT_RUN_NS : SOAK_RUN_NS;
        runStartNs = System.nanoTime();
        runEndNs = runStartNs + duration;
        nextDueNs = runStartNs;
        lastProgressNsValue = runStartNs;
        Log.i(TAG, "R12B_START mode=" + mode + " width=" + WIDTH + " height=" + HEIGHT +
                " bytes=" + FRAME_BYTES + " target_fps=30 duration_ns=" + duration +
                " source_pid=" + android.os.Process.myPid());
        scheduler.post(frameTick);
    }

    private void offerTick() {
        if (!running || finishPending) return;
        long now = System.nanoTime();
        if (now >= runEndNs) {
            finishPending = true;
            if (!inFlight) ui.post(new Runnable() { public void run() { finishTimedRun(); } });
            return;
        }
        offered++;
        if (inFlight || remote == null) {
            dropBackpressure++;
        } else {
            inFlight = true;
            maxInFlight = 1;
            final long offerTime = now;
            final long currentSequence = ++sequence;
            sender.post(new Runnable() {
                public void run() { sendSyntheticFrame(currentSequence, offerTime); }
            });
        }
        logProgressIfDue(now);
        nextDueNs += FRAME_INTERVAL_NS;
        long delayMs = Math.max(0L, (nextDueNs - System.nanoTime()) / 1000000L);
        scheduler.postDelayed(frameTick, delayMs);
    }

    private void sendSyntheticFrame(long currentSequence, long offerTime) {
        byte[] pixels = new byte[FRAME_BYTES];
        byte marker = (byte) (currentSequence & 0xff);
        Arrays.fill(pixels, marker);
        long pts = offerTime;
        DecodedFrame frame;
        ParcelFileDescriptor descriptor = null;
        try {
            frame = new DecodedFrame(WIDTH, HEIGHT, STRIDE, pts, 0, 0, 0,
                    WIDTH, HEIGHT, ByteBuffer.wrap(pixels));
            byte[] parcelBytes = MessengerFrameParcel.rgba(frame);
            descriptor = MessengerFrameParcel.write(parcelBytes);
            Bundle data = new Bundle();
            data.putInt(MessengerFrameHostService.KEY_WIDTH, WIDTH);
            data.putInt(MessengerFrameHostService.KEY_HEIGHT, HEIGHT);
            data.putInt(MessengerFrameHostService.KEY_STRIDE, STRIDE);
            data.putInt(MessengerFrameHostService.KEY_BYTES, FRAME_BYTES);
            data.putLong(MessengerFrameHostService.KEY_PTS, pts);
            data.putInt(MessengerFrameHostService.KEY_ROTATION, 0);
            data.putInt(MessengerFrameHostService.KEY_CROP_LEFT, 0);
            data.putInt(MessengerFrameHostService.KEY_CROP_TOP, 0);
            data.putInt(MessengerFrameHostService.KEY_CROP_RIGHT, WIDTH);
            data.putInt(MessengerFrameHostService.KEY_CROP_BOTTOM, HEIGHT);
            data.putLong(MessengerFrameHostService.KEY_GENERATION, generation);
            data.putLong(MessengerFrameHostService.KEY_SEQUENCE, currentSequence);
            data.putParcelable(MessengerFrameHostService.KEY_PFD, descriptor);
            Message request = Message.obtain(null, MessengerFrameHostService.FRAME);
            request.replyTo = replies;
            request.setData(data);
            sentAtNs = offerTime;
            activeFrame = frame;
            sent++;
            remote.send(request);
        } catch (Exception failure) {
            if (descriptor != null) close(descriptor);
            final String reason = failure.getClass().getSimpleName();
            ui.post(new Runnable() {
                public void run() {
                    activeFrame = null;
                    inFlight = false;
                    transportErrors++;
                    Log.e(TAG, "R12B_FRAME_SEND_FAILED sequence=" + sequence + " reason=" + reason);
                    if (finishPending) finishTimedRun();
                }
            });
        } finally {
            if (descriptor != null) close(descriptor);
        }
    }

    private void onReply(Message message) {
        Bundle data = message.getData();
        String replyKind = data.getString(MessengerFrameHostService.KEY_REASON);
        if (message.arg1 == MessengerFrameHostService.STATS) {
            captureHostStats(data, "baseline_stats".equals(replyKind));
            return;
        }
        if (message.arg1 != MessengerFrameHostService.FRAME) return;
        if (data.getLong(MessengerFrameHostService.KEY_GENERATION, -1L) != generation) {
            close(data.<ParcelFileDescriptor>getParcelable(MessengerFrameHostService.KEY_PFD));
            hostRejected++;
            inFlight = false;
            activeFrame = null;
            if (finishPending) finishTimedRun();
            return;
        }
        if (!data.getBoolean(MessengerFrameHostService.KEY_ACCEPTED)) {
            close(data.<ParcelFileDescriptor>getParcelable(MessengerFrameHostService.KEY_PFD));
            inFlight = false;
            activeFrame = null;
            captureHostStats(data, false);
            if (preflightStage == 1) {
                partialFrameRejected = "short_frame_payload".equals(
                        data.getString(MessengerFrameHostService.KEY_REASON));
                preflightStage = 2;
                Log.i(TAG, "R12B_PARTIAL_FRAME_REJECTED reason=" +
                        data.getString(MessengerFrameHostService.KEY_REASON) +
                        " passed=" + partialFrameRejected);
                sendControl(MessengerFrameHostService.STATS, "baseline_stats");
                return;
            }
            hostRejected++;
            if (finishPending) finishTimedRun();
            return;
        }
        ParcelFileDescriptor returned = data.getParcelable(MessengerFrameHostService.KEY_PFD);
        try {
            byte[] result = MessengerFrameParcel.read(returned,
                    data.getInt(MessengerFrameHostService.KEY_BYTES));
            if (activeFrame == null || !Arrays.equals(MessengerFrameParcel.rgba(activeFrame), result)) {
                pixelMismatches++;
                throw new IOException("pixel_identity_failure");
            }
            DecodedFrame deliveredFrame = MessengerFrameParcel.decoded(WIDTH, HEIGHT, STRIDE,
                    data.getLong(MessengerFrameHostService.KEY_PTS), 0, 0, 0, WIDTH, HEIGHT, result);
            if (renderer == null) {
                renderer = new Display1OutputBackend(new HondaStyleSimulatorRendererHost(simulator),
                        new Display1OutputBackend.Viewport(0, 0, 800, 480), generation);
                renderer.attach();
            }
            renderer.submit(deliveredFrame);
            hostAccepted++;
            delivered++;
            if (latencyCount < latencyNs.length) latencyNs[latencyCount++] = System.nanoTime() - sentAtNs;
            captureHostStats(data, false);
        } catch (Exception failure) {
            transportErrors++;
            Log.e(TAG, "R12B_DELIVERY_FAILED delivered=" + delivered, failure);
        } finally {
            inFlight = false;
            activeFrame = null;
        }
        if (finishPending) finishTimedRun();
    }

    private void captureHostStats(Bundle data, boolean baseline) {
        hostPidBaseline = data.getInt(MessengerFrameHostService.KEY_HOST_PID, -1);
        int hostFds = data.getInt(MessengerFrameHostService.KEY_HOST_FDS, -1);
        long hostJava = data.getLong(MessengerFrameHostService.KEY_HOST_JAVA_USED, -1L);
        long hostNative = data.getLong(MessengerFrameHostService.KEY_HOST_NATIVE_HEAP, -1L);
        if (baseline) {
            hostFdBaseline = hostFds;
            hostJavaBaseline = hostJava;
            hostNativeBaseline = hostNative;
        }
        hostFdFinal = hostFds;
        hostJavaFinal = hostJava;
        hostNativeFinal = hostNative;
        hostMemoryFilesCreated = data.getLong(MessengerFrameHostService.KEY_HOST_MEMORY_FILES_CREATED);
        hostMemoryFilesClosed = data.getLong(MessengerFrameHostService.KEY_HOST_MEMORY_FILES_CLOSED);
        hostMemoryFilesOpen = data.getLong(MessengerFrameHostService.KEY_HOST_MEMORY_FILES_OPEN);
        hostReads = data.getLong(MessengerFrameHostService.KEY_HOST_READS);
        hostReadBytes = data.getLong(MessengerFrameHostService.KEY_HOST_READ_BYTES);
        if (baseline && !running && preflightStage == 0) {
            preflightStage = 1;
            sendPartialFrame();
        } else if (baseline && !running && preflightStage == 2) {
            ui.postDelayed(new Runnable() { public void run() { startRun(); } }, 500L);
        }
        if ("final_stats".equals(data.getString(MessengerFrameHostService.KEY_REASON))) {
            finalStatsReceived = true;
            logFinalResult(null);
            ui.postDelayed(new Runnable() { public void run() { finish(); } }, 500L);
        }
    }

    private void sendPartialFrame() {
        if (remote == null) { finishWithError("host_missing_for_partial_frame"); return; }
        ParcelFileDescriptor descriptor = null;
        try {
            descriptor = MessengerFrameParcel.write(new byte[8]);
            Bundle data = new Bundle();
            data.putInt(MessengerFrameHostService.KEY_WIDTH, 2);
            data.putInt(MessengerFrameHostService.KEY_HEIGHT, 2);
            data.putInt(MessengerFrameHostService.KEY_STRIDE, 8);
            data.putInt(MessengerFrameHostService.KEY_BYTES, 16);
            data.putLong(MessengerFrameHostService.KEY_PTS, System.nanoTime());
            data.putLong(MessengerFrameHostService.KEY_GENERATION, generation);
            data.putLong(MessengerFrameHostService.KEY_SEQUENCE, 1L);
            data.putParcelable(MessengerFrameHostService.KEY_PFD, descriptor);
            Message request = Message.obtain(null, MessengerFrameHostService.FRAME);
            request.replyTo = replies;
            request.setData(data);
            inFlight = true;
            remote.send(request);
        } catch (Exception failure) {
            if (descriptor != null) close(descriptor);
            inFlight = false;
            finishWithError("partial_frame_preflight_failed:" + failure.getClass().getSimpleName());
        } finally { if (descriptor != null) close(descriptor); }
    }

    private void logProgressIfDue(long now) {
        if (now - lastProgressNs < 1000000000L) return;
        long elapsed = now - runStartNs;
        double fps = (delivered - lastProgressDelivered) * 1000000000.0 /
                Math.max(1L, now - lastProgressNsValue);
        Log.i(TAG, "R12B_PROGRESS mode=" + mode + " elapsed_s=" + (elapsed / 1000000000.0) +
                " offered=" + offered + " sent=" + sent + " host_accepted=" + hostAccepted +
                " delivered=" + delivered + " drop_backpressure=" + dropBackpressure +
                " renderer_fps_1s=" + fps + " in_flight=" + (inFlight ? 1 : 0));
        lastProgressNs = now;
        lastProgressNsValue = now;
        lastProgressDelivered = delivered;
    }

    private void finishTimedRun() {
        if (!running) return;
        running = false;
        finishPending = false;
        runEndNs = System.nanoTime();
        closeRenderer();
        simulator.setNavigationActive(false);
        sendControl(MessengerFrameHostService.DETACH, "run_detach");
        System.gc();
        System.runFinalization();
        ui.postDelayed(finishStats, 5000L);
    }

    private void requestFinalStats() {
        if (remote == null) {
            logFinalResult("host_missing_before_final_stats");
            finish();
            return;
        }
        producerFdFinal = fdCount();
        Runtime runtime = Runtime.getRuntime();
        producerJavaFinal = runtime.totalMemory() - runtime.freeMemory();
        producerNativeFinal = Debug.getNativeHeapAllocatedSize();
        sendControl(MessengerFrameHostService.STATS, "final_stats");
    }

    private void logFinalResult(String error) {
        double seconds = Math.max(0.001, (runEndNs - runStartNs) / 1000000000.0);
        long[] sorted = Arrays.copyOf(latencyNs, latencyCount);
        Arrays.sort(sorted);
        double fpsOffered = offered / seconds;
        double fpsAccepted = hostAccepted / seconds;
        double fpsDelivered = delivered / seconds;
        double throughputMb = delivered * (double) FRAME_BYTES / seconds / 1000000.0;
        int dropped = Math.max(0, offered - delivered - hostRejected - transportErrors);
        Log.i(TAG, "R12B_RESULT mode=" + mode + " error=" + error +
                " elapsed_s=" + seconds + " width=" + WIDTH + " height=" + HEIGHT +
                " offered=" + offered + " offered_fps=" + fpsOffered + " sent=" + sent +
                " host_accepted=" + hostAccepted + " accepted_fps=" + fpsAccepted +
                " delivered=" + delivered + " delivered_fps=" + fpsDelivered +
                " dropped=" + dropped + " dropped_backpressure=" + dropBackpressure +
                " host_rejected=" + hostRejected + " transport_errors=" + transportErrors +
                " pixel_mismatches=" + pixelMismatches + " queue_high_water=" + maxInFlight +
                " partial_frame_rejected=" + partialFrameRejected +
                " latency_p50_ms=" + percentile(sorted, 0.50) / 1000000.0 +
                " latency_p95_ms=" + percentile(sorted, 0.95) / 1000000.0 +
                " latency_p99_ms=" + percentile(sorted, 0.99) / 1000000.0 +
                " latency_max_ms=" + (sorted.length == 0 ? 0 : sorted[sorted.length - 1] / 1000000.0) +
                " delivered_MiB_s=" + (delivered * (double) FRAME_BYTES / seconds / (1024.0 * 1024.0)) +
                " delivered_MB_s=" + throughputMb + " source_fd_base=" + producerFdBaseline +
                " source_fd_final=" + producerFdFinal + " source_java_base=" + producerJavaBaseline +
                " source_java_final=" + producerJavaFinal + " source_native_base=" + producerNativeBaseline +
                " source_native_final=" + producerNativeFinal + " host_pid=" + hostPidBaseline +
                " host_fd_base=" + hostFdBaseline + " host_fd_final=" + hostFdFinal +
                " host_java_base=" + hostJavaBaseline + " host_java_final=" + hostJavaFinal +
                " host_native_base=" + hostNativeBaseline + " host_native_final=" + hostNativeFinal +
                " source_memoryfiles_created=" + MessengerFrameParcel.memoryFilesCreated() +
                " source_memoryfiles_closed=" + MessengerFrameParcel.memoryFilesClosed() +
                " source_memoryfiles_open=" + MessengerFrameParcel.memoryFilesOpen() +
                " source_reads=" + MessengerFrameParcel.readsCompleted() +
                " source_read_bytes=" + MessengerFrameParcel.readBytes() +
                " host_memoryfiles_created=" + hostMemoryFilesCreated +
                " host_memoryfiles_closed=" + hostMemoryFilesClosed +
                " host_memoryfiles_open=" + hostMemoryFilesOpen +
                " host_reads=" + hostReads + " host_read_bytes=" + hostReadBytes +
                " final_stats=" + finalStatsReceived);
        if (status != null) status.setText("CL-R12-B " + mode + " finished; see emulator log");
    }

    private static long percentile(long[] sorted, double fraction) {
        if (sorted.length == 0) return 0L;
        int index = Math.min(sorted.length - 1,
                Math.max(0, (int) Math.ceil(fraction * sorted.length) - 1));
        return sorted[index];
    }

    private void sendControl(int what, String reason) {
        if (remote == null) return;
        Message message = Message.obtain(null, what);
        message.replyTo = replies;
        Bundle data = new Bundle();
        data.putLong(MessengerFrameHostService.KEY_GENERATION, generation);
        data.putString(MessengerFrameHostService.KEY_REASON, reason);
        message.setData(data);
        try { remote.send(message); }
        catch (RemoteException failure) { finishWithError("control_ipc_closed:" + reason); }
    }

    private void closeRenderer() {
        if (renderer == null) return;
        try { renderer.close(); }
        catch (RuntimeException failure) { Log.e(TAG, "R12B_RENDERER_CLOSE_FAILED", failure); }
        renderer = null;
    }

    private void finishWithError(String reason) {
        if (running) {
            running = false;
            finishPending = false;
            runEndNs = System.nanoTime();
            logFinalResult(reason);
        } else Log.e(TAG, "R12B_SETUP_FAILED reason=" + reason);
        ui.postDelayed(new Runnable() { public void run() { finish(); } }, 250L);
    }

    private static int fdCount() {
        String[] descriptors = new File("/proc/self/fd").list();
        return descriptors == null ? -1 : descriptors.length;
    }

    private static void close(ParcelFileDescriptor descriptor) {
        if (descriptor != null) try { descriptor.close(); } catch (IOException ignored) { }
    }

    @Override protected void onDestroy() {
        if (scheduler != null) scheduler.removeCallbacks(frameTick);
        ui.removeCallbacks(finishStats);
        closeRenderer();
        if (simulator != null && !simulator.isClosed()) simulator.close();
        if (bound) { unbindService(connection); bound = false; }
        if (schedulerThread != null) schedulerThread.quit();
        if (senderThread != null) senderThread.quit();
        super.onDestroy();
    }
}
