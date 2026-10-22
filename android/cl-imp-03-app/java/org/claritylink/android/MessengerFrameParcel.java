package org.claritylink.android;

import android.os.MemoryFile;
import android.os.ParcelFileDescriptor;

import org.claritylink.renderer.DecodedFrame;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.lang.reflect.Method;
import java.nio.ByteBuffer;
import java.util.concurrent.atomic.AtomicLong;

/** Bounded MemoryFile/PFD serializer for the offline Messenger renderer lab. */
final class MessengerFrameParcel {
    static final class IoTiming {
        long allocationNs;
        long writeNs;
        long descriptorNs;
        long readNs;
        long closeNs;
    }
    static final int MAX_BYTES = 4 * 1024 * 1024;
    private static final AtomicLong MEMORY_FILES_CREATED = new AtomicLong();
    private static final AtomicLong MEMORY_FILES_OPEN = new AtomicLong();
    private static final AtomicLong MEMORY_FILES_CLOSED = new AtomicLong();
    private static final AtomicLong MEMORY_BYTES_CREATED = new AtomicLong();
    private static final AtomicLong READS_COMPLETED = new AtomicLong();
    private static final AtomicLong READ_BYTES = new AtomicLong();

    static ParcelFileDescriptor write(byte[] bytes) throws IOException {
        return write(bytes, null);
    }

    static ParcelFileDescriptor write(byte[] bytes, IoTiming timing) throws IOException {
        if (bytes == null || bytes.length == 0 || bytes.length > MAX_BYTES)
            throw new IOException("frame_size_out_of_range");
        long started = timing == null ? 0L : System.nanoTime();
        MemoryFile memory = new MemoryFile("claritylink-synthetic-frame", bytes.length);
        if (timing != null) {
            timing.allocationNs = System.nanoTime() - started;
            started = System.nanoTime();
        }
        MEMORY_FILES_CREATED.incrementAndGet();
        MEMORY_FILES_OPEN.incrementAndGet();
        MEMORY_BYTES_CREATED.addAndGet(bytes.length);
        ParcelFileDescriptor descriptor = null;
        try {
            if (timing != null) started = System.nanoTime();
            memory.writeBytes(bytes, 0, 0, bytes.length);
            if (timing != null) timing.writeNs = System.nanoTime() - started;
            if (timing != null) started = System.nanoTime();
            Method getter = MemoryFile.class.getDeclaredMethod("getFileDescriptor");
            getter.setAccessible(true);
            descriptor = ParcelFileDescriptor.dup((java.io.FileDescriptor) getter.invoke(memory));
            if (timing != null) timing.descriptorNs = System.nanoTime() - started;
        } catch (Exception failure) {
            throw new IOException("memory_file_descriptor_unavailable", failure);
        } finally {
            if (timing != null) started = System.nanoTime();
            memory.close();
            if (timing != null) timing.closeNs = System.nanoTime() - started;
            MEMORY_FILES_CLOSED.incrementAndGet();
            MEMORY_FILES_OPEN.decrementAndGet();
        }
        return descriptor;
    }

    static byte[] read(ParcelFileDescriptor descriptor, int expectedBytes) throws IOException {
        return read(descriptor, expectedBytes, null);
    }

    static byte[] read(ParcelFileDescriptor descriptor, int expectedBytes, IoTiming timing)
            throws IOException {
        return read(descriptor, expectedBytes, timing, null);
    }

    /**
     * Reads exactly {@code expectedBytes}. When {@code into} has exactly that length it is filled and
     * returned instead of allocating a new array; the caller then owns the rule that it is not read or
     * kept past the point where the next read into it begins.
     */
    static byte[] read(ParcelFileDescriptor descriptor, int expectedBytes, IoTiming timing, byte[] into)
            throws IOException {
        if (descriptor == null || expectedBytes <= 0 || expectedBytes > MAX_BYTES)
            throw new IOException("invalid_frame_descriptor");
        long started = timing == null ? 0L : System.nanoTime();
        InputStream input = new ParcelFileDescriptor.AutoCloseInputStream(descriptor);
        try {
            byte[] result = (into != null && into.length == expectedBytes) ? into : new byte[expectedBytes];
            int offset = 0;
            while (offset < expectedBytes) {
                int count = input.read(result, offset, expectedBytes - offset);
                if (count < 0) throw new IOException("short_frame_payload");
                offset += count;
            }
            if (input.read() != -1) throw new IOException("oversized_frame_payload");
            if (timing != null) timing.readNs = System.nanoTime() - started;
            READS_COMPLETED.incrementAndGet();
            READ_BYTES.addAndGet(expectedBytes);
            return result;
        } finally {
            if (timing != null) started = System.nanoTime();
            input.close();
            if (timing != null) timing.closeNs = System.nanoTime() - started;
        }
    }

    static byte[] rgba(DecodedFrame frame) throws IOException {
        if (frame == null || frame.byteSize() <= 0 || frame.byteSize() > MAX_BYTES)
            throw new IOException("invalid_decoded_frame");
        ByteArrayOutputStream output = new ByteArrayOutputStream(frame.byteSize());
        frame.writeRgbaTo(output);
        return output.toByteArray();
    }

    static DecodedFrame decoded(int width, int height, int stride, long ptsNs,
            int rotation, int left, int top, int right, int bottom, byte[] rgba) {
        return new DecodedFrame(width, height, stride, ptsNs, rotation, left, top,
                right, bottom, ByteBuffer.wrap(rgba));
    }

    static long memoryFilesCreated() { return MEMORY_FILES_CREATED.get(); }
    static long memoryFilesOpen() { return MEMORY_FILES_OPEN.get(); }
    static long memoryFilesClosed() { return MEMORY_FILES_CLOSED.get(); }
    static long memoryBytesCreated() { return MEMORY_BYTES_CREATED.get(); }
    static long readsCompleted() { return READS_COMPLETED.get(); }
    static long readBytes() { return READ_BYTES.get(); }

    private MessengerFrameParcel() { }
}
