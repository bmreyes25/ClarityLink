package org.claritylink.android;

public final class OfflinePolicyTest {
    private static void require(boolean value,String message) { if(!value) throw new AssertionError(message); }
    public static void main(String[] args) {
        require(!DisplayPolicy.WarningVisibilityPolicy.unknown().safeForHonda(),"UNKNOWN warning evidence must fail closed");
        DisplayPolicy.WarningVisibilityPolicy approved=new DisplayPolicy.WarningVisibilityPolicy(
            DisplayPolicy.Evidence.APPROVED,true,false,true,true);
        require(approved.safeForHonda(),"explicit warning and protected-region evidence accepted");
        DisplayPolicy.WarningVisibilityPolicy incomplete=new DisplayPolicy.WarningVisibilityPolicy(
            DisplayPolicy.Evidence.APPROVED,false,false,true,true);
        require(!incomplete.safeForHonda(),"approved label alone must not promote unsafe warning policy");
        java.util.Map<String,CapabilityEvidence.Fact> facts=new java.util.HashMap<String,CapabilityEvidence.Fact>();
        facts.put("usb_ownership",new CapabilityEvidence.Fact("owned",CapabilityEvidence.Level.DOCUMENTED_ANDROID,"API17 docs"));
        CapabilityEvidence evidence=new CapabilityEvidence(1,facts);
        require(!evidence.permits("usb_ownership","owned",CapabilityEvidence.Level.HONDA_STATIC),
            "Android USB documentation cannot prove Honda USB ownership");
        facts.put("warning_policy",new CapabilityEvidence.Fact("safe",CapabilityEvidence.Level.UNKNOWN,"none"));
        evidence=new CapabilityEvidence(1,facts);
        require(!evidence.permits("warning_policy","safe",CapabilityEvidence.Level.HONDA_PROTOTYPE_OBSERVED),
            "UNKNOWN capability cannot be promoted");
        require(DisplayPolicy.FULL_FRAME_TEST_LAYOUT.testOnly,"full-frame layout is test-only");
        require(!DisplayPolicy.WarningVisibilityPolicy.unknown().safeForHonda(),"unknown warnings never imply safe rendering");
        boolean zeroAreaRejected=false;
        try { new DisplayPolicy.Layout(800,480,0,0,0,100,0,false); }
        catch(IllegalArgumentException expected) { zeroAreaRejected=true; }
        require(zeroAreaRejected,"zero-sized area rejected");
        boolean outOfBoundsRejected=false;
        try { new DisplayPolicy.Layout(800,480,799,0,2,10,0,false); }
        catch(IllegalArgumentException expected) { outOfBoundsRejected=true; }
        require(outOfBoundsRejected,"out-of-bounds area rejected");
        boolean invalidRotationRejected=false;
        try { new DisplayPolicy.Layout(800,480,0,0,100,100,45,false); }
        catch(IllegalArgumentException expected) { invalidRotationRejected=true; }
        require(invalidRotationRejected,"unsupported rotation rejected");
        MockPrimaryDisplayHost mock=new MockPrimaryDisplayHost();
        require(mock.attach(7,800,480),"mock primary attach");
        require(!mock.frame(8,800,480),"mock rejects stale generation");
        require(mock.frame(7,800,480) && mock.hasFrame(),"mock primary frame");
        mock.detach(); require(!mock.hasFrame() && !mock.isAttached(),"mock primary detach clears frame");
        MemoryAudioAdapter audio=new MemoryAudioAdapter();
        require(!audio.open(1,1,16),"audio rejects invalid format");
        require(audio.open(48000,2,16),"audio opens valid format");
        require(audio.write(new byte[16],0,16),"audio bounded write");
        require(!audio.write(new byte[3],0,3),"audio rejects unaligned PCM frame");
        audio.pause(); require(audio.isPaused(),"audio pause"); audio.resume(); require(!audio.isPaused(),"audio resume");
        audio.flush(); require(audio.bytesWritten()==0,"audio flush"); audio.close(); audio.close(); require(!audio.isOpen(),"audio idempotent close");
        require(!audio.write(new byte[1],0,1),"audio rejects write after close");
        MemoryAudioAdapter boundedAudio=new MemoryAudioAdapter(); require(boundedAudio.open(48000,2,16),"audio reopens");
        require(!boundedAudio.write(new byte[AndroidAudioAdapter.MAX_WRITE_BYTES+1],0,AndroidAudioAdapter.MAX_WRITE_BYTES+1),"audio write bounded");
        boundedAudio.close();
        java.util.Set<String> allowed=new java.util.HashSet<String>(); allowed.add("TOUCH:1:2");
        InputBridge input=new InputBridge(allowed);
        require(input.accept(new InputBridge.Event(1,InputBridge.Kind.TOUCH,2,1,10,5),5),"allowlisted input accepted");
        require(!input.accept(new InputBridge.Event(1,InputBridge.Kind.STEERING,99,1,10,5),5),"unknown control mapping rejected");
        require(!input.accept(new InputBridge.Event(1,InputBridge.Kind.TOUCH,2,1,10,4),5),"stale input generation rejected");
        require(!SessionBoundaries.AndroidAuthenticationAdapter.unavailableHondaDefault().authenticate(1),"default Honda auth unavailable");
        require(!SessionBoundaries.AndroidAuthenticationAdapter.unavailableHondaDefault().genuineAuthority(),"unavailable auth is not genuine");
        require(!new SessionBoundaries.UnavailableIap2().ready(),"default iAP2 unavailable");
        require(!new MediaTransports.CarPlayMediaTransport().ready(),"real CarPlay framing disabled by default");
        boolean testModeRequired=false;
        try { new MediaTransports.SyntheticMediaTransport(1,false); }
        catch(IllegalArgumentException expected) { testModeRequired=true; }
        require(testModeRequired,"synthetic envelope requires explicit lab mode");

        for(int cycle=0;cycle<100;cycle++) {
            final int[] count={0};
            ProcessLifecycleAdapter lifecycle=new ProcessLifecycleAdapter();
            ProcessLifecycleAdapter.Receiver receiver=new ProcessLifecycleAdapter.Receiver() {
                boolean active;
                public boolean start() { active=true; return true; }
                public void disconnect() { active=false; count[0]++; }
                public void stop() { active=false; }
                public boolean active() { return active; }
            };
            require(lifecycle.start(receiver),"start cycle");
            lifecycle.own(new ProcessLifecycleAdapter.OwnedResource() {
                public String name() { return "offline-surface"; }
                public boolean closeAndVerify() { count[0]++; return true; }
            });
            require(lifecycle.activate(),"activate cycle");
            require(lifecycle.stop(receiver),"restore cycle");
            require(lifecycle.state()==ProcessLifecycleAdapter.State.STOPPED,"stopped state");
            require(count[0]==2,"owned cleanup accounting");
        }
        System.out.println("R7C_POLICY_AND_PROCESS_PASS unknown_warning=FAIL_CLOSED lifecycle_cycles=100");
    }
}
