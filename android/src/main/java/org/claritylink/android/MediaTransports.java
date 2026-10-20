package org.claritylink.android;

/** Synthetic R7B framing is an explicit lab transport; real CarPlay framing is unavailable. */
public final class MediaTransports {
    public interface Transport { boolean ready(); boolean submit(byte[] bytes,long generation); void close(); }
    public static final class SyntheticMediaTransport implements Transport {
        private final long receiverHandle;
        private final boolean explicitLabMode;
        public SyntheticMediaTransport(long receiverHandle,boolean explicitLabMode) {
            if(receiverHandle<=0 || !explicitLabMode) throw new IllegalArgumentException("synthetic transport requires explicit lab mode");
            this.receiverHandle=receiverHandle; this.explicitLabMode=true;
        }
        public boolean ready() { return explicitLabMode; }
        public boolean submit(byte[] packet,long generation) {
            return packet!=null && generation>0 && NativeBridge.nativeTestIngestSyntheticPacket(receiverHandle,generation,packet);
        }
        public void close() { }
    }
    /** No production wire framing exists yet; default construction always fails closed. */
    public static final class CarPlayMediaTransport implements Transport {
        public boolean ready() { return false; }
        public boolean submit(byte[] bytes,long generation) { return false; }
        public void close() { }
    }
    private MediaTransports() {}
}
