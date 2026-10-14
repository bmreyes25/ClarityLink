package org.claritylink.android;

import android.app.Service;
import android.content.Intent;
import android.os.Binder;
import android.os.IBinder;
import android.os.Parcel;
import android.os.ParcelFileDescriptor;
import android.os.Process;
import android.os.RemoteException;
import android.util.Log;

import org.claritylink.renderer.SimulatedExternalDisplayCompositor;

import java.io.FileInputStream;
import java.io.IOException;

/** Private second-process compositor endpoint for the emulator lab only. */
public final class CompositorService extends Service {
    private static final String TAG = "ClarityLinkCLIMP03";
    private final SimulatedExternalDisplayCompositor compositor =
            new SimulatedExternalDisplayCompositor();
    private final IBinder endpoint = new Binder() {
        @Override protected boolean onTransact(int code, Parcel data, Parcel reply, int flags)
                throws RemoteException {
            if (Binder.getCallingUid() != Process.myUid()) {
                reply.writeException(new SecurityException("private compositor caller rejected"));
                return true;
            }
            data.enforceInterface(FrameIpcProtocol.DESCRIPTOR);
            int version = data.readInt();
            if (version != FrameIpcProtocol.VERSION) {
                reply.writeException(new IllegalArgumentException("unsupported IPC version"));
                return true;
            }
            if (code == FrameIpcProtocol.BEGIN) {
                long generation = data.readLong();
                boolean accepted = compositor.begin(generation);
                Log.i(TAG, "IPC_REMOTE_BEGIN pid=" + Process.myPid() + " generation=" + generation
                        + " accepted=" + accepted);
                reply.writeNoException();
                reply.writeInt(accepted ? 1 : 0);
                reply.writeInt(Process.myPid());
                return true;
            }
            if (code == FrameIpcProtocol.END) {
                long generation = data.readLong();
                boolean accepted = compositor.end(generation);
                Log.i(TAG, "IPC_REMOTE_END generation=" + generation + " accepted=" + accepted
                        + " resources_cleared=" + (compositor.activeGeneration() == 0));
                reply.writeNoException();
                reply.writeInt(accepted ? 1 : 0);
                return true;
            }
            if (code == FrameIpcProtocol.WARNING) {
                long generation = data.readLong();
                boolean visible = data.readInt() != 0;
                boolean accepted = compositor.setWarningVisible(generation, visible);
                Log.i(TAG, "IPC_REMOTE_WARNING generation=" + generation + " visible=" + visible
                        + " accepted=" + accepted + " retained_frame_bytes="
                        + compositor.latestPayloadBytes());
                reply.writeNoException();
                reply.writeInt(accepted ? 1 : 0);
                return true;
            }
            if (code == FrameIpcProtocol.FRAME) {
                receiveFrame(data, reply);
                return true;
            }
            return super.onTransact(code, data, reply, flags);
        }
    };

    @Override public void onCreate() {
        super.onCreate();
        Log.i(TAG, "IPC_REMOTE_PROCESS_READY pid=" + Process.myPid());
    }

    @Override public IBinder onBind(Intent intent) { return endpoint; }

    @Override public void onDestroy() {
        long generation = compositor.activeGeneration();
        if (generation > 0) compositor.end(generation);
        Log.i(TAG, "IPC_REMOTE_PROCESS_DESTROYED resources_cleared=" +
                (compositor.activeGeneration() == 0));
        super.onDestroy();
    }

    private void receiveFrame(Parcel data, Parcel reply) {
        long generation = data.readLong();
        long timestampNs = data.readLong();
        int width = data.readInt();
        int height = data.readInt();
        int rowStride = data.readInt();
        int payloadBytes = data.readInt();
        ParcelFileDescriptor descriptor = data.readParcelable(
                ParcelFileDescriptor.class.getClassLoader());
        boolean payloadValid = false;
        try {
            payloadValid = descriptor != null && readBoundedPayload(descriptor, payloadBytes);
        } catch (IOException failure) {
            Log.i(TAG, "IPC_REMOTE_FRAME_IO_REJECT type=" + failure.getClass().getSimpleName());
        }
        boolean accepted = payloadValid && compositor.accept(generation, timestampNs,
                width, height, rowStride, payloadBytes);
        Log.i(TAG, "IPC_REMOTE_FRAME generation=" + generation + " timestamp=" + timestampNs
                + " bytes=" + payloadBytes + " accepted=" + accepted
                + " bounded=true retained_frame_bytes=0");
        reply.writeNoException();
        reply.writeInt(accepted ? 1 : 0);
    }

    private static boolean readBoundedPayload(ParcelFileDescriptor descriptor, int expectedBytes)
            throws IOException {
        if (expectedBytes <= 0 || expectedBytes > FrameIpcProtocol.MAX_FRAME_BYTES) {
            descriptor.close();
            return false;
        }
        FileInputStream input = new ParcelFileDescriptor.AutoCloseInputStream(descriptor);
        try {
            byte[] chunk = new byte[8192];
            int remaining = expectedBytes;
            while (remaining > 0) {
                int count = input.read(chunk, 0, Math.min(chunk.length, remaining));
                if (count < 0) return false;
                remaining -= count;
            }
            return input.read() == -1;
        } finally {
            input.close();
        }
    }
}
