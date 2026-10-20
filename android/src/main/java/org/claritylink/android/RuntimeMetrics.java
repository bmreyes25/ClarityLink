package org.claritylink.android;

import java.util.concurrent.atomic.AtomicLong;

/** Bounded aggregate counters only; no phone, VIN, address, or session identifiers. */
public final class RuntimeMetrics {
    private static final long MAX=Long.MAX_VALUE;
    private final AtomicLong decodeNanos=new AtomicLong(), deliveryNanos=new AtomicLong(), dropped=new AtomicLong();
    private final AtomicLong queueDepth=new AtomicLong(), audioUnderruns=new AtomicLong(), socketErrors=new AtomicLong();
    private final AtomicLong surfaceRecreates=new AtomicLong(), resourceCount=new AtomicLong();
    private static void add(AtomicLong counter,long amount) {
        if(amount<0) return;
        for(;;) { long old=counter.get(), next=old>MAX-amount?MAX:old+amount; if(counter.compareAndSet(old,next)) return; }
    }
    public void decoded(long nanos) { add(decodeNanos,nanos); }
    public void delivered(long nanos) { add(deliveryNanos,nanos); }
    public void droppedFrame() { add(dropped,1); }
    public void setQueueDepth(long depth) { queueDepth.set(Math.min(4096,Math.max(0,depth))); }
    public void audioUnderrun() { add(audioUnderruns,1); }
    public void socketError() { add(socketErrors,1); }
    public void surfaceRecreated() { add(surfaceRecreates,1); }
    public void setResourceCount(long count) { resourceCount.set(Math.min(1000000,Math.max(0,count))); }
    public long[] snapshot() { return new long[]{decodeNanos.get(),deliveryNanos.get(),dropped.get(),queueDepth.get(),
        audioUnderruns.get(),socketErrors.get(),surfaceRecreates.get(),resourceCount.get()}; }
}
