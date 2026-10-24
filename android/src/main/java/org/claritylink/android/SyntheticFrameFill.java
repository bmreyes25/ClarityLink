package org.claritylink.android;

/**
 * Fills a synthetic frame buffer with one repeated byte.
 *
 * The CL-R12 producer rewrites an 800x480 RGBA frame (1.5 MB) for every offered frame.
 * {@code Arrays.fill(byte[], byte)} is a Java loop on Dalvik, so that rewrite cost
 * milliseconds of the 33 ms frame budget on the producer's own thread. This writes a short
 * seed and doubles it with {@code System.arraycopy} (a native copy). The resulting bytes are
 * identical to {@code Arrays.fill}; only the cost of producing them changes.
 */
final class SyntheticFrameFill {
    private static final int SEED = 4096;

    static void fill(byte[] destination, byte value) {
        int length = destination.length;
        if (length == 0) return;
        int seed = Math.min(length, SEED);
        for (int i = 0; i < seed; i++) destination[i] = value;
        int filled = seed;
        while (filled < length) {
            int chunk = Math.min(filled, length - filled);
            System.arraycopy(destination, 0, destination, filled, chunk);
            filled += chunk;
        }
    }

    private SyntheticFrameFill() { }
}
