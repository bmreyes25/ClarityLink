package org.claritylink.android;

import android.app.Service;
import android.content.Intent;
import android.os.Binder;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.Parcel;
import android.os.Process;
import android.os.RemoteException;
import android.util.Base64;
import android.util.Log;

import org.claritylink.renderer.DecodedFrame;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/** Private API17 laboratory H.264 producer, isolated from the Type111 Activity/View process. */
public final class Type111ProducerService extends Service {
    private static final String TAG = "ClarityLinkCLIMP03";
    private static final String DESCRIPTOR = "org.claritylink.android.IType111LabProducer";
    private static final int START_PRODUCER = IBinder.FIRST_CALL_TRANSACTION;
    private static final int TERMINATE_PRODUCER = IBinder.FIRST_CALL_TRANSACTION + 1;
    private static final int QUERY_PID = IBinder.FIRST_CALL_TRANSACTION + 2;
    private static final long MAX_WAIT_MS = 15000L;
    private static final int MAX_IN_FLIGHT = 1;
    private volatile boolean running;
    private volatile boolean completed;
    private volatile CountDownLatch runFinished = new CountDownLatch(1);
    private final long[] submittedTimestamps = new long[4];
    private int submittedCount;

    private final IBinder control = new Binder() {
        @Override protected boolean onTransact(int code, Parcel data, Parcel reply, int flags)
                throws RemoteException {
            if (Binder.getCallingUid() != Process.myUid()) {
                reply.writeException(new SecurityException("private producer caller rejected"));
                return true;
            }
            data.enforceInterface(DESCRIPTOR);
            if (code == START_PRODUCER) {
                int ownerPid = Binder.getCallingPid();
                if (!isAuthorizedViewCaller(ownerPid)) {
                    Log.w(TAG, "TYPE111_PRODUCER_CONTROL_REJECT operation=start caller_pid=" + ownerPid);
                    reply.writeNoException(); reply.writeInt(0); reply.writeInt(Process.myPid());
                    return true;
                }
                IBinder endpoint = data.readStrongBinder();
                IBinder sink = data.readStrongBinder();
                FrameStreamIdentity identity = readIdentity(data);
                long nextFrameId = data.readLong();
                long firstPtsUs = data.readLong();
                boolean expandFirstFrameForTransferTest = data.dataAvail() > 0 && data.readInt() != 0;
                boolean accepted = startProducer(endpoint, sink, identity, nextFrameId, firstPtsUs,
                        ownerPid, expandFirstFrameForTransferTest);
                reply.writeNoException();
                reply.writeInt(accepted ? 1 : 0);
                reply.writeInt(Process.myPid());
                return true;
            }
            if (code == TERMINATE_PRODUCER) {
                int ownerPid = Binder.getCallingPid();
                if (!isAuthorizedViewCaller(ownerPid)) {
                    Log.w(TAG, "TYPE111_PRODUCER_CONTROL_REJECT operation=terminate caller_pid=" + ownerPid);
                    reply.writeNoException(); reply.writeInt(0); reply.writeInt(Process.myPid());
                    return true;
                }
                boolean accepted = running || completed;
                reply.writeNoException();
                reply.writeInt(accepted ? 1 : 0);
                reply.writeInt(Process.myPid());
                if (accepted) new Handler(Looper.getMainLooper()).postDelayed(new Runnable() {
                    public void run() { Process.killProcess(Process.myPid()); }
                }, 150L);
                return true;
            }
            if (code == QUERY_PID) {
                reply.writeNoException();
                reply.writeInt(Process.myPid());
                reply.writeInt(running ? 1 : 0);
                reply.writeInt(completed ? 1 : 0);
                synchronized (Type111ProducerService.this) {
                    reply.writeInt(submittedCount);
                    for (int i = 0; i < submittedCount; i++) reply.writeLong(submittedTimestamps[i]);
                }
                return true;
            }
            if (code == IBinder.FIRST_CALL_TRANSACTION + 3) {
                long timeout = data.readLong();
                if (timeout < 0L || timeout > MAX_WAIT_MS) {
                    Log.w(TAG, "TYPE111_PRODUCER_WAIT_REJECT pid=" + Process.myPid() +
                            " timeout_ms=" + timeout + " maximum_ms=" + MAX_WAIT_MS);
                    reply.writeNoException();
                    reply.writeInt(0);
                    reply.writeInt(0);
                    return true;
                }
                boolean done = false;
                try { done = runFinished.await(timeout, TimeUnit.MILLISECONDS); }
                catch (InterruptedException interrupted) { Thread.currentThread().interrupt(); }
                reply.writeNoException();
                reply.writeInt(done ? 1 : 0);
                synchronized (Type111ProducerService.this) {
                    reply.writeInt(submittedCount);
                    for (int i = 0; i < submittedCount; i++) reply.writeLong(submittedTimestamps[i]);
                }
                return true;
            }
            return super.onTransact(code, data, reply, flags);
        }
    };

    @Override public IBinder onBind(Intent intent) {
        Log.i(TAG, "TYPE111_PRODUCER_BOUND component=Type111ProducerService process=:type111_producer " +
                "pid=" + Process.myPid() + " uid=" + Process.myUid());
        return control;
    }

    private synchronized boolean startProducer(final IBinder endpoint, final IBinder sink,
            final FrameStreamIdentity identity, final long nextFrameId, final long firstPtsUs,
            final int ownerPid, final boolean expandFirstFrameForTransferTest) {
        if (running || endpoint == null || sink == null || identity == null ||
                identity.streamType != FrameStreamIdentity.TYPE111 ||
                identity.outputId != FrameStreamIdentity.OUTPUT_SECONDARY_VIEW ||
                !identity.isValid() || nextFrameId <= 0 || nextFrameId == Long.MAX_VALUE ||
                firstPtsUs <= 0 || firstPtsUs > 60000000L) return false;
        if (!authorizeWithCompositor(endpoint, identity, ownerPid)) return false;
        if (completed) {
            completed = false;
            submittedCount = 0;
            runFinished = new CountDownLatch(1);
        }
        final FrameIpcClient client = FrameIpcClient.attachExistingType111(
                endpoint, identity, nextFrameId);
        if (client == null) return false;
        running = true;
        Log.i(TAG, "TYPE111_PRODUCER_START pid=" + Process.myPid() + " session_id=" +
                identity.sessionId + " connection_id=" + identity.connectionId +
                " transport_generation=" + identity.streamGeneration + " output_id=" +
                identity.outputId + " compositor_binder_alive=" + endpoint.isBinderAlive() +
                " sink_binder_alive=" + sink.isBinderAlive());
        try {
            new Thread(new Runnable() {
                public void run() { decodeAndSubmit(client, identity, firstPtsUs,
                        expandFirstFrameForTransferTest); }
            }, "ClarityLinkType111IsolatedProducer").start();
        } catch (RuntimeException startupFailure) {
            rollbackProducerStart();
            throw startupFailure;
        } catch (Error startupFailure) {
            rollbackProducerStart();
            throw startupFailure;
        }
        return true;
    }

    private boolean authorizeWithCompositor(IBinder endpoint, FrameStreamIdentity identity, int ownerPid) {
        Parcel data = Parcel.obtain(), reply = Parcel.obtain();
        try {
            data.writeInterfaceToken(FrameIpcProtocol.DESCRIPTOR);
            data.writeInt(FrameIpcProtocol.VERSION);
            data.writeInt(ownerPid);
            data.writeLong(identity.sessionId); data.writeInt(identity.streamType);
            data.writeLong(identity.connectionId); data.writeLong(identity.streamGeneration);
            data.writeInt(identity.outputId);
            if (!endpoint.transact(FrameIpcProtocol.TYPE111_PRODUCER_AUTHORIZE, data, reply, 0)) return false;
            reply.readException();
            return reply.readInt() != 0;
        } catch (RemoteException failure) {
            Log.w(TAG, "TYPE111_PRODUCER_AUTHORIZATION_FAILED", failure);
            return false;
        } finally { reply.recycle(); data.recycle(); }
    }

    private boolean isAuthorizedViewCaller(int pid) {
        android.app.ActivityManager manager = (android.app.ActivityManager)
                getSystemService(ACTIVITY_SERVICE);
        if (manager == null) return false;
        java.util.List<android.app.ActivityManager.RunningAppProcessInfo> processes =
                manager.getRunningAppProcesses();
        if (processes == null) return false;
        String expected = getPackageName() + ":type111_view";
        for (android.app.ActivityManager.RunningAppProcessInfo process : processes)
            if (process.pid == pid) return expected.equals(process.processName);
        return false;
    }

    private synchronized void rollbackProducerStart() {
        running = false;
        completed = true;
        runFinished.countDown();
    }

    private void decodeAndSubmit(FrameIpcClient client, FrameStreamIdentity identity, long firstPtsUs,
            boolean expandFirstFrameForTransferTest) {
        Api17BufferH264Decoder decoder = null;
        try {
            byte[] encoded = readFixture("type111-blue-32x32.h264.b64");
            byte[] fixture = Base64.decode(encoded, Base64.DEFAULT);
            byte[] config = Api17SurfaceH264Decoder.extractCodecConfig(fixture);
            byte[][] accessUnits = Api17SurfaceH264Decoder.extractVclFrames(fixture);
            if (accessUnits.length < 2 || (accessUnits[0][4] & 31) != 5)
                throw new IllegalStateException("isolated_producer_fixture_missing_idr");
            final long decoderGeneration = 1000000L + identity.streamGeneration;
            decoder = new Api17BufferH264Decoder(32, 32, decoderGeneration, config);
            int submitted = 0;
            for (int index = 0; index < 16 && submitted < 2; index++) {
                DecodedFrame frame = decoder.decode(accessUnits[index % accessUnits.length], firstPtsUs +
                        index * 100000L, decoderGeneration, 3000L);
                if (frame == null) continue;
                if (expandFirstFrameForTransferTest && submitted == 0) {
                    int sourceWidth = frame.width;
                    int sourceHeight = frame.height;
                    frame = expandFrameForTransferTest(frame);
                    Log.i(TAG, "TYPE111_PRODUCER_TRANSFER_TEST_FRAME_EXPANDED pid=" + Process.myPid() +
                            " source=" + sourceWidth + "x" + sourceHeight +
                            " transfer=" + frame.width + "x" + frame.height +
                            " bytes=" + frame.byteSize());
                }
                final CountDownLatch complete = new CountDownLatch(1);
                final boolean[] accepted = new boolean[1];
                final String[] reason = new String[] { "callback_missing" };
                if (!client.submit(frame, identity.streamGeneration, new FrameIpcClient.Callback() {
                    public void complete(boolean result, String failure) {
                        accepted[0] = result;
                        reason[0] = failure;
                        complete.countDown();
                    }
                })) throw new IllegalStateException("isolated_producer_submit_not_started");
                if (!complete.await(10L, TimeUnit.SECONDS) || !accepted[0])
                    throw new IllegalStateException("isolated_producer_frame_rejected:" + reason[0]);
                synchronized (this) {
                    if (submittedCount >= submittedTimestamps.length)
                        throw new IllegalStateException("isolated_producer_timestamp_bound_exceeded");
                    submittedTimestamps[submittedCount++] = frame.presentationTimeNs;
                }
                Log.i(TAG, "TYPE111_PRODUCER_FRAME_ACCEPTED pid=" + Process.myPid() +
                        " session_id=" + identity.sessionId + " connection_id=" + identity.connectionId +
                        " transport_generation=" + identity.streamGeneration + " frame_id=" +
                        (client.nextFrameIdHint() - 1L) + " decoded=true binder_pfd=true width=" +
                        frame.width + " height=" + frame.height + " timestamp_ns=" +
                        frame.presentationTimeNs + " in_flight_bound=" + MAX_IN_FLIGHT);
                submitted++;
            }
            if (submitted < 1) throw new IllegalStateException("isolated_producer_no_decoded_frames");
            Log.i(TAG, "TYPE111_PRODUCER_RUN_PASS pid=" + Process.myPid() + " session_id=" +
                    identity.sessionId + " connection_id=" + identity.connectionId +
                    " generation=" + identity.streamGeneration + " submitted=" + submitted +
                    " decoder_generation=" + decoderGeneration + " resources_released=true");
        } catch (Throwable failure) {
            Log.e(TAG, "TYPE111_PRODUCER_RUN_FAIL pid=" + Process.myPid() + " type=" +
                    failure.getClass().getSimpleName() + " message=" + failure.getMessage(), failure);
        } finally {
            if (decoder != null) decoder.close();
            running = false;
            completed = true;
            runFinished.countDown();
        }
    }

    private static DecodedFrame expandFrameForTransferTest(DecodedFrame source) throws Exception {
        final int scale = 8;
        final int width = source.width * scale;
        final int height = source.height * scale;
        final int rowStride = width * 4;
        ByteArrayOutputStream encoded = new ByteArrayOutputStream(source.byteSize());
        source.writeRgbaTo(encoded);
        byte[] input = encoded.toByteArray();
        byte[] output = new byte[rowStride * height];
        for (int y = 0; y < height; y++) {
            int sourceY = y / scale;
            for (int x = 0; x < width; x++) {
                int sourceOffset = sourceY * source.rowStride + (x / scale) * 4;
                int outputOffset = y * rowStride + x * 4;
                output[outputOffset] = input[sourceOffset];
                output[outputOffset + 1] = input[sourceOffset + 1];
                output[outputOffset + 2] = input[sourceOffset + 2];
                output[outputOffset + 3] = input[sourceOffset + 3];
            }
        }
        return new DecodedFrame(width, height, rowStride, source.presentationTimeNs,
                source.rotationDegrees, 0, 0, width, height, java.nio.ByteBuffer.wrap(output));
    }

    private byte[] readFixture(String name) throws Exception {
        InputStream input = getAssets().open(name);
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        byte[] buffer = new byte[1024];
        int count;
        try {
            while ((count = input.read(buffer)) != -1) {
                if (bytes.size() + count > 16384) throw new IllegalStateException("fixture_size_limit");
                bytes.write(buffer, 0, count);
            }
        } finally { input.close(); }
        return bytes.toByteArray();
    }

    private static FrameStreamIdentity readIdentity(Parcel data) {
        return new FrameStreamIdentity(data.readLong(), data.readInt(), data.readLong(),
                data.readLong(), data.readInt());
    }
}
