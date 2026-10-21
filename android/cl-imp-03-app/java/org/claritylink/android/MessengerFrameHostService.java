package org.claritylink.android;

import android.app.Service;
import android.content.Intent;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.Message;
import android.os.Messenger;
import android.os.ParcelFileDescriptor;
import android.os.Process;
import android.os.RemoteException;
import android.os.Debug;
import android.util.Log;

import java.io.File;
import java.io.IOException;

/** Separate-process synthetic Navigation-frame host for API17 Messenger/PFD experiments. */
public final class MessengerFrameHostService extends Service {
    static final int ATTACH = 1;
    static final int FRAME = 2;
    static final int PAGE = 3;
    static final int INTERRUPT = 4;
    static final int DETACH = 5;
    static final int CRASH_FIXTURE = 6;
    static final int STATS = 7;
    static final int ACK = 100;
    static final String KEY_PFD = "synthetic_frame_pfd";
    static final String KEY_WIDTH = "width";
    static final String KEY_HEIGHT = "height";
    static final String KEY_STRIDE = "stride";
    static final String KEY_PTS = "pts_ns";
    static final String KEY_SEQUENCE = "sequence";
    static final String KEY_GENERATION = "generation";
    static final String KEY_ROTATION = "rotation";
    static final String KEY_CROP_LEFT = "crop_left";
    static final String KEY_CROP_TOP = "crop_top";
    static final String KEY_CROP_RIGHT = "crop_right";
    static final String KEY_CROP_BOTTOM = "crop_bottom";
    static final String KEY_BYTES = "frame_bytes";
    static final String KEY_ACCEPTED = "accepted";
    static final String KEY_REASON = "reason";
    static final String KEY_HOST_PID = "host_pid";
    static final String KEY_HOST_JAVA_USED = "host_java_used";
    static final String KEY_HOST_JAVA_MAX = "host_java_max";
    static final String KEY_HOST_NATIVE_HEAP = "host_native_heap";
    static final String KEY_HOST_FDS = "host_fds";
    static final String KEY_HOST_MEMORY_FILES_OPEN = "host_memory_files_open";
    static final String KEY_HOST_MEMORY_FILES_CLOSED = "host_memory_files_closed";
    static final String KEY_HOST_MEMORY_FILES_CREATED = "host_memory_files_created";
    static final String KEY_HOST_MEMORY_BYTES = "host_memory_bytes_created";
    static final String KEY_HOST_READS = "host_reads_completed";
    static final String KEY_HOST_READ_BYTES = "host_read_bytes";

    private static final String TAG = "ClarityLinkMessengerLab";
    private long generation;
    private long lastSequence;
    private boolean navigation;
    private boolean interrupted;
    private int inFlight;

    private final Messenger endpoint = new Messenger(new Handler(Looper.getMainLooper()) {
        @Override public void handleMessage(Message message) {
            handle(message);
        }
    });

    @Override public IBinder onBind(Intent intent) { return endpoint.getBinder(); }

    private void handle(Message message) {
        if (message.what == ATTACH) {
            long requested = message.getData().getLong(KEY_GENERATION);
            if (requested > generation) {
                generation = requested;
                lastSequence = 0L;
                navigation = true;
                interrupted = false;
                reply(message, true, "attached", null);
            } else reply(message, false, "stale_generation", null);
            return;
        }
        if (message.what == PAGE || message.what == INTERRUPT) {
            if (message.getData().getLong(KEY_GENERATION) != generation) {
                reply(message, false, "stale_generation", null);
                return;
            }
            if (message.what == PAGE) navigation = message.arg1 != 0;
            else interrupted = message.arg1 != 0;
            reply(message, true, message.what == PAGE ? "page_updated" : "interrupt_updated", null);
            return;
        }
        if (message.what == DETACH) {
            boolean current = message.getData().getLong(KEY_GENERATION) == generation;
            if (current) {
                navigation = false;
                interrupted = false;
                generation++;
                lastSequence = 0L;
            }
            reply(message, current, current ? "detached" : "stale_generation", null);
            return;
        }
        if (message.what == CRASH_FIXTURE) {
            Log.w(TAG, "LAB_ONLY_SYNTHETIC_HOST_PROCESS_CRASH pid=" + Process.myPid());
            new Handler().postDelayed(new Runnable() {
                public void run() { Process.killProcess(Process.myPid()); }
            }, 100L);
            return;
        }
        if (message.what == STATS) {
            if ("final_stats".equals(message.getData().getString(KEY_REASON))) {
                System.gc();
                System.runFinalization();
            }
            reply(message, true, "stats", null);
            return;
        }
        if (message.what == FRAME) receiveFrame(message);
    }

    private void receiveFrame(Message message) {
        android.os.Bundle data = message.getData();
        long requestedGeneration = data.getLong(KEY_GENERATION, -1L);
        long sequence = data.getLong(KEY_SEQUENCE, -1L);
        int width = data.getInt(KEY_WIDTH, 0);
        int height = data.getInt(KEY_HEIGHT, 0);
        int stride = data.getInt(KEY_STRIDE, 0);
        int byteCount = data.getInt(KEY_BYTES, 0);
        ParcelFileDescriptor incoming = data.getParcelable(KEY_PFD);
        if (requestedGeneration != generation || sequence <= lastSequence) {
            close(incoming); reply(message, false, "stale_frame", null); return;
        }
        if (!navigation || interrupted) {
            close(incoming); reply(message, false, interrupted ? "interrupt_preemption" : "navigation_inactive", null); return;
        }
        long expected = (long) stride * height;
        if (width <= 0 || height <= 0 || width > 1920 || height > 1080 ||
                stride < (long) width * 4L || expected != byteCount || expected > MessengerFrameParcel.MAX_BYTES) {
            close(incoming); reply(message, false, "invalid_frame_geometry", null); return;
        }
        inFlight++;
        try {
            byte[] pixels = MessengerFrameParcel.read(incoming, byteCount);
            ParcelFileDescriptor returned = MessengerFrameParcel.write(pixels);
            lastSequence = sequence;
            Log.i(TAG, "MESSENGER_FRAME_ACCEPTED generation=" + generation + " sequence=" + sequence +
                    " bytes=" + byteCount + " in_flight=" + inFlight + " process=" + Process.myPid());
            reply(message, true, "accepted", returned);
        } catch (IOException failure) {
            close(incoming);
            reply(message, false, failure.getMessage(), null);
        } finally { inFlight--; }
    }

    private static void close(ParcelFileDescriptor descriptor) {
        if (descriptor != null) try { descriptor.close(); } catch (IOException ignored) { }
    }

    private static void reply(Message request, boolean accepted, String reason,
            ParcelFileDescriptor pixels) {
        if (request.replyTo == null) { close(pixels); return; }
        Message response = Message.obtain(null, ACK);
        response.arg1 = request.what;
        android.os.Bundle data = new android.os.Bundle();
        data.putBoolean(KEY_ACCEPTED, accepted);
        data.putString(KEY_REASON, request.what == STATS
                ? request.getData().getString(KEY_REASON, reason) : reason);
        Runtime runtime = Runtime.getRuntime();
        data.putInt(KEY_HOST_PID, Process.myPid());
        data.putLong(KEY_HOST_JAVA_USED, runtime.totalMemory() - runtime.freeMemory());
        data.putLong(KEY_HOST_JAVA_MAX, runtime.maxMemory());
        data.putLong(KEY_HOST_NATIVE_HEAP, Debug.getNativeHeapAllocatedSize());
        data.putInt(KEY_HOST_FDS, openFileDescriptorCount());
        data.putLong(KEY_HOST_MEMORY_FILES_OPEN, MessengerFrameParcel.memoryFilesOpen());
        data.putLong(KEY_HOST_MEMORY_FILES_CLOSED, MessengerFrameParcel.memoryFilesClosed());
        data.putLong(KEY_HOST_MEMORY_FILES_CREATED, MessengerFrameParcel.memoryFilesCreated());
        data.putLong(KEY_HOST_MEMORY_BYTES, MessengerFrameParcel.memoryBytesCreated());
        data.putLong(KEY_HOST_READS, MessengerFrameParcel.readsCompleted());
        data.putLong(KEY_HOST_READ_BYTES, MessengerFrameParcel.readBytes());
        data.putLong(KEY_GENERATION, request.getData().getLong(KEY_GENERATION, -1L));
        data.putLong(KEY_SEQUENCE, request.getData().getLong(KEY_SEQUENCE, -1L));
        for (String key : new String[] { KEY_WIDTH, KEY_HEIGHT, KEY_STRIDE, KEY_PTS, KEY_ROTATION,
                KEY_CROP_LEFT, KEY_CROP_TOP, KEY_CROP_RIGHT, KEY_CROP_BOTTOM, KEY_BYTES })
            if (request.getData().containsKey(key)) data.putInt(key, request.getData().getInt(key));
        if (request.getData().containsKey(KEY_PTS))
            data.putLong(KEY_PTS, request.getData().getLong(KEY_PTS));
        if (pixels != null) data.putParcelable(KEY_PFD, pixels);
        response.setData(data);
        try { request.replyTo.send(response); }
        catch (RemoteException failure) { close(pixels); }
        finally { close(pixels); }
    }

    private static int openFileDescriptorCount() {
        String[] descriptors = new File("/proc/self/fd").list();
        return descriptors == null ? -1 : descriptors.length;
    }
}
