package org.claritylink.android;

import java.util.ArrayList;
import java.util.List;

/** Project-owned temporary start/run/stop lifecycle; no persistent startup hooks. */
public final class ProcessLifecycleAdapter {
    public enum State { STOPPED, STARTING, READY, ACTIVE, DISCONNECTING, RESTORING, FAULTED }
    public interface OwnedResource { String name(); boolean closeAndVerify(); }
    public interface Receiver { boolean start(); void disconnect(); void stop(); boolean active(); }
    private State state=State.STOPPED;
    private final List<OwnedResource> resources=new ArrayList<OwnedResource>();
    private String lastErrorType="";
    public synchronized State state() { return state; }
    public synchronized String lastErrorType() { return lastErrorType; }
    public synchronized void own(OwnedResource resource) {
        if (state==State.STOPPED || state==State.RESTORING || resource==null) throw new IllegalStateException("resource outside active lifecycle");
        resources.add(resource);
    }
    public synchronized boolean start(Receiver receiver) {
        if(state!=State.STOPPED || receiver==null) return false;
        state=State.STARTING;
        try { if(!receiver.start()) { state=State.FAULTED; return false; } state=State.READY; return true; }
        catch(RuntimeException e) { lastErrorType=e.getClass().getName(); state=State.FAULTED; return false; }
    }
    public synchronized boolean activate() { if(state!=State.READY) return false; state=State.ACTIVE; return true; }
    public synchronized boolean stop(Receiver receiver) {
        if(state==State.STOPPED) return true;
        state=State.DISCONNECTING;
        if(receiver!=null) {
            try { receiver.disconnect(); } catch(RuntimeException e) { lastErrorType=e.getClass().getName(); }
            try { receiver.stop(); } catch(RuntimeException e) { lastErrorType=e.getClass().getName(); }
        }
        state=State.RESTORING;
        boolean clean=receiver==null || !receiver.active();
        for(int i=resources.size()-1;i>=0;i--) {
            try { clean=resources.get(i).closeAndVerify() && clean; }
            catch(RuntimeException e) { lastErrorType=e.getClass().getName(); clean=false; }
        }
        resources.clear(); state=clean?State.STOPPED:State.FAULTED; return clean;
    }
}
