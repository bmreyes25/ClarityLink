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
    static final int MAX_BYTES = 4 * 1024 * 1024;
    private static final AtomicLong MEMORY_FILES_CREATED = new AtomicLong();
    private static final AtomicLong MEMORY_FILES_OPEN = new AtomicLong();
    private static final AtomicLong MEMORY_FILES_CLOSED = new AtomicLong();
    private static final AtomicLong MEMORY_BYTES_CREATED = new AtomicLong();
    private static final AtomicLong READS_COMPLETED = new AtomicLong();
    private static final AtomicLong READ_BYTES = new AtomicLong();

    static ParcelFileDescriptor write(byte[] bytes) throws IOException {
        if (bytes == null || bytes.length == 0 || bytes.length > MAX_BYTES)
            throw new IOException("frame_size_out_of_range");
        MemoryFile memory = new MemoryFile("claritylink-synthetic-frame", bytes.length);
        MEMORY_FILES_CREATED.incrementAndGet();
        MEMORY_FILES_OPEN.incrementAndGet();
        MEMORY_BYTES_CREATED.addAndGet(bytes.length);
        ParcelFileDescriptor descriptor = null;
        try {
            memory.writeBytes(bytes, 0, 0, bytes.length);
            Method getter = MemoryFile.class.getDeclaredMethod("getFileDescriptor");
            getter.setAccessible(true);
            descriptor = ParcelFileDescriptor.dup((java.io.FileDescriptor) getter.invoke(memory));
        } catch (Exception failure) {
            throw new IOException("memory_file_descriptor_unavailable", failure);
        } finally {
            memory.close();
            MEMORY_FILES_CLOSED.incrementAndGet();
            MEMORY_FILES_OPEN.decrementAndGet();
        }
        return descriptor;
    }

    static byte[] read(ParcelFileDescriptor descriptor, int expectedBytes) throws IOException {
        if (descriptor == null || expectedBytes <= 0 || expectedBytes > MAX_BYTES)
            throw new IOException("invalid_frame_descriptor");
        InputStream input = new ParcelFileDescriptor.AutoCloseInputStream(descriptor);
        try {
            byte[] result = new byte[expectedBytes];
            int offset = 0;
            while (offset < expectedBytes) {
                int count = input.read(result, offset, expectedBytes - offset);
                if (count < 0) throw new IOException("short_frame_payload");
                offset += count;
            }
            if (input.read() != -1) throw new IOException("oversized_frame_payload");
            READS_COMPLETED.incrementAndGet();
            READ_BYTES.addAndGet(expectedBytes);
            return result;
        } finally {
            input.close();
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
