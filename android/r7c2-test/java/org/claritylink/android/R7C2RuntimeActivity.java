package org.claritylink.android;

import android.app.Activity;
import android.content.Context;
import android.hardware.display.DisplayManager;
import android.hardware.usb.UsbManager;
import android.media.AudioFormat;
import android.os.Bundle;
import android.os.Debug;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.util.Base64;
import android.util.Log;
import android.view.Display;
import android.view.Gravity;
import android.view.Surface;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.widget.FrameLayout;
import java.io.ByteArrayOutputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.ServerSocket;
import java.net.Socket;
import java.io.OutputStream;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/** Explicit emulator-only R7C2 instrumentation; all media/auth inputs are synthetic lab data. */
public final class R7C2RuntimeActivity extends Activity {
    private static final String TAG = "ClarityLinkR7C2";
    private final Object surfaceLock = new Object();
    private Surface primarySurface;
    private Surface fallbackSecondarySurface;
    private Surface presentationSurface;
    private SurfaceView fallbackView;
    private PrimaryDisplayHost primaryView;
    private FrameLayout rootView;
    private SecondaryDisplayHost secondaryHost;
    private Display secondaryDisplay;
    private volatile CountDownLatch secondarySurfaceCreated;
    private volatile CountDownLatch secondarySurfaceDestroyed;
    private CountDownLatch primarySurfaceDestroyed;
    private volatile CountDownLatch primarySurfaceCreated;
    private volatile long activeRaceReceiver;
    private volatile long activeRacePrimarySurface;
    private volatile long activeRaceSecondarySurface;
    private volatile boolean activeSocketRace;
    private AndroidAudioAdapter activityDestroyAudio;
    private InputBridge activityDestroyInput;
    private final CountDownLatch activityDestroyed = new CountDownLatch(1);
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private volatile CountDownLatch destructionHeartbeat;
    private boolean started;
    private String runtimeFailure;
    private volatile String activeTestCase = "startup";
    private final long activityGeneration = SystemClock.elapsedRealtimeNanos();

    public void onCreate(Bundle state) {
        super.onCreate(state);
        record("ACTIVITY_CREATED");
        rootView = new FrameLayout(this);
        primaryView = new PrimaryDisplayHost(this);
        PrimaryDisplayHost primary = primaryView;
        primary.setListener(new PrimaryDisplayHost.Listener() {
            public void onSurface(Surface surface) {
                record(surface == null ? "PRIMARY_SURFACE_DESTROYED" : "PRIMARY_SURFACE_CREATED");
                synchronized(surfaceLock) { primarySurface=surface; }
                CountDownLatch created=primarySurfaceCreated;
                if(created!=null) created.countDown();
                maybeStart();
            }
            public void onSurfaceLost() {
                synchronized(surfaceLock) { primarySurface=null; }
                long handle=activeRacePrimarySurface; activeRacePrimarySurface=0;
                if(handle>0) { NativeBridge.nativeReleaseSurface(handle); record("PRIMARY_SURFACE_NATIVE_OWNER_RELEASED"); }
                final CountDownLatch heartbeat=destructionHeartbeat;
                if(heartbeat!=null)mainHandler.post(new Runnable(){public void run(){record("POST_SURFACE_MAIN_LOOPER_HEARTBEAT");heartbeat.countDown();}});
                CountDownLatch destroyed=primarySurfaceDestroyed;
                if(destroyed!=null) destroyed.countDown();
            }
        });
        fallbackView = new SurfaceView(this);
        fallbackView.getHolder().addCallback(new SurfaceHolder.Callback() {
            public void surfaceCreated(SurfaceHolder holder) { record("SECONDARY_SURFACE_CREATED"); synchronized(surfaceLock) { fallbackSecondarySurface=holder.getSurface(); } maybeStart(); }
            public void surfaceChanged(SurfaceHolder holder,int format,int width,int height) { }
            public void surfaceDestroyed(SurfaceHolder holder) { record("SECONDARY_SURFACE_DESTROYED"); synchronized(surfaceLock) { fallbackSecondarySurface=null; } }
        });
        FrameLayout.LayoutParams p = new FrameLayout.LayoutParams(640,480,Gravity.TOP|Gravity.LEFT);
        rootView.addView(primary,p);
        FrameLayout.LayoutParams f = new FrameLayout.LayoutParams(240,180,Gravity.BOTTOM|Gravity.RIGHT);
        rootView.addView(fallbackView,f);
        setContentView(rootView);
        record("PROCESS_READY api="+android.os.Build.VERSION.SDK_INT+" runtime="+System.getProperty("java.vm.name"));
        enumerateDisplays();
    }

    private void runDeterministicRaceSuite(final Surface primary, final byte[] h110,
                                           final byte[] h111) throws Exception {
        assertRaceIdle("suite-start");
        runSetupCancellationRace(primary, h110, false);
        assertRaceIdle("after-setup-primary");
        runSetupCancellationRace(primary, h110, true);
        assertRaceIdle("after-setup-secondary");
        runDecodeCancellationRace(primary, h110, h111, 110);
        assertRaceIdle("after-decode-primary");
        for(int i=0;i<25;i++) {
            runDecodeCancellationRace(primary,h110,h111,111);
            assertRaceIdle("after-type111-decode-cancel-"+i);
        }
        runFrameworkPrimarySurfaceDestroyRace(primary, h110);
        assertRaceIdle("after-primary-surface");
        runFrameworkSecondarySurfaceDestroyRace(primary, h110, h111, false);
        assertRaceIdle("after-type111-surface-1");
        for(int i=1;i<25;i++) { runFrameworkSecondarySurfaceDestroyRace(primary,h110,h111,false); assertRaceIdle("after-type111-surface-"+i); }
        for(int i=0;i<25;i++) { runType111PeerCloseIsolation(primary,h110); assertRaceIdle("after-peer-close-"+i); }
        runFrameworkSecondarySurfaceDestroyRace(primary, h110, h111, true);
        assertRaceIdle("after-presentation-dismiss-1");
        for(int i=1;i<25;i++) {
            recreateSecondaryPresentation();
            runFrameworkSecondarySurfaceDestroyRace(primary,h110,h111,true);
            assertRaceIdle("after-presentation-dismiss-"+i);
        }
        runNativeSocketReadShutdownRace();
        assertRaceIdle("after-socket-read-shutdown");
        runNativeSocketWriteShutdownRace();
        assertRaceIdle("after-socket-write-shutdown");
        runActivityDestroyDuringDualStream(primary,h110,h111);
        assertRaceIdle("after-activity-destroy");
        record("R7C6_DETERMINISTIC_RACE_SUITE=PASS type111_surface=25 presentation=25 peer_close=25");
    }

    private void recreateSecondaryPresentation() throws Exception {
        if(secondaryDisplay==null || !secondaryDisplay.isValid())
            throw new IllegalStateException("synthetic secondary Display unavailable for Presentation recreation");
        secondarySurfaceCreated=new CountDownLatch(1);
        runOnUiThread(new Runnable(){public void run(){
            secondaryHost=new SecondaryDisplayHost(new SecondaryDisplayHost.Listener(){
                public void state(DisplayPolicy.Admission state){record("PRESENTATION_STATE="+state.name());}
                public void surface(Surface surface){
                    synchronized(surfaceLock){presentationSurface=surface;}
                    if(surface==null){
                        record("SECONDARY_SURFACE_DESTROYED");
                        long handle=activeRaceSecondarySurface;activeRaceSecondarySurface=0;
                        if(handle>0){NativeBridge.nativeReleaseSurface(handle);record("SECONDARY_SINK_INVALIDATED");}
                        CountDownLatch destroyed=secondarySurfaceDestroyed;
                        if(destroyed!=null)destroyed.countDown();
                    }else{
                        CountDownLatch created=secondarySurfaceCreated;
                        if(created!=null)created.countDown();
                    }
                    maybeStart();
                }
                public void error(String operation,String type){record("PRESENTATION_ERROR="+operation+":"+type);}
            });
            if(!secondaryHost.showOfflineLabForRuntimeTest(R7C2RuntimeActivity.this,secondaryDisplay,
                    1001,DisplayPolicy.FULL_FRAME_TEST_LAYOUT))
                record("PRESENTATION_RECREATE_REJECTED");
        }});
        if(!secondarySurfaceCreated.await(5,TimeUnit.SECONDS)||presentationSurface==null)
            throw new IllegalStateException("secondary Presentation Surface recreation timed out");
    }

    private void runType111PeerCloseIsolation(final Surface primary,final byte[] h110)throws Exception{
        final long generation=40500;
        final Surface secondary=presentationSurface!=null?presentationSurface:fallbackSecondarySurface;
        final long p=NativeBridge.nativeAttachSurface(primary,generation,110,generation*2);
        final long s=NativeBridge.nativeAttachSurface(secondary,generation,111,generation*2+1);
        final long receiver=NativeBridge.nativeCreateReceiver(generation,p,s,true);
        if(!NativeBridge.nativeSetup(receiver,generation,1100,1101,true))
            throw new IllegalStateException("Type111 peer-close SETUP failed");
        final ServerSocket server=new ServerSocket(0,1,java.net.InetAddress.getByName("127.0.0.1"));
        final CountDownLatch accepted=new CountDownLatch(1);
        Thread peer=new Thread(new Runnable(){public void run(){
            try{Socket socket=server.accept();accepted.countDown();socket.close();}
            catch(Throwable t){record("TYPE111_PEER_CLOSE_PEER_ERROR="+t.getClass().getSimpleName());}
        }},"r7c6-type111-peer-close");
        peer.start();
        final boolean[] delivered={true};
        Thread read=new Thread(new Runnable(){public void run(){
            delivered[0]=R7C3TestBridge.receiveSocketFrame(receiver,generation,"127.0.0.1",
                    server.getLocalPort(),3000,111);
        }},"r7c6-type111-peer-reader");
        read.start();
        if(!accepted.await(5,TimeUnit.SECONDS))throw new IllegalStateException("Type111 peer was not accepted");
        read.join(5000);peer.join(5000);server.close();
        long[] counts=NativeBridge.nativeDebugResourceCounts();
        if(read.isAlive()||peer.isAlive()||delivered[0]||counts[4]!=1||counts[5]!=1||
                !NativeBridge.nativeTestIngestSyntheticPacket(receiver,generation,packet(generation,110,1100,h110)))
            throw new IllegalStateException("Type111 peer close did not isolate and preserve Type110");
        NativeBridge.nativeDisconnect(receiver);NativeBridge.nativeReleaseReceiver(receiver);
        NativeBridge.nativeReleaseSurface(p);NativeBridge.nativeReleaseSurface(s);
        requireNativeZero("Type111 peer close cleanup");
        record("TYPE111_PEER_CLOSE_ISOLATION=PASS");
    }

    private void runActivityDestroyDuringDualStream(final Surface primary,final byte[] h110,final byte[] h111)throws Exception{
        final long generation=40610;
        final Surface secondary=presentationSurface!=null?presentationSurface:fallbackSecondarySurface;
        final long p=NativeBridge.nativeAttachSurface(primary,generation,110,generation*2);
        final long s=NativeBridge.nativeAttachSurface(secondary,generation,111,generation*2+1);
        final long receiver=NativeBridge.nativeCreateReceiver(generation,p,s,true);
        if(!NativeBridge.nativeSetup(receiver,generation,1100,1101,true))
            throw new IllegalStateException("Activity-destroy SETUP failed");
        assertRaceIdle("activity-destroy-before");
        if(!NativeBridge.nativeTestIngestSyntheticPacket(receiver,generation,packet(generation,110,1100,h110)) ||
                !NativeBridge.nativeTestIngestSyntheticPacket(receiver,generation,packet(generation,111,1101,h111)))
            throw new IllegalStateException("Activity-destroy dual-stream decode/post did not become active");
        activeRaceReceiver=receiver;activeRacePrimarySurface=p;activeRaceSecondarySurface=s;
        activityDestroyAudio=new AndroidAudioAdapter(this);
        if(!activityDestroyAudio.open(44100,2,AudioFormat.ENCODING_PCM_16BIT))
            throw new IllegalStateException("Activity-destroy AudioTrack could not open");
        activityDestroyInput=new InputBridge(Collections.<String>emptySet());
        final ServerSocket primaryServer=new ServerSocket(0,1,java.net.InetAddress.getByName("127.0.0.1"));
        final ServerSocket secondaryServer=new ServerSocket(0,1,java.net.InetAddress.getByName("127.0.0.1"));
        final CountDownLatch accepted=new CountDownLatch(2);
        Thread primaryPeer=waitForSocketClose(primaryServer,accepted,"r7c7-activity-primary-peer");
        Thread secondaryPeer=waitForSocketClose(secondaryServer,accepted,"r7c7-activity-secondary-peer");
        primaryPeer.start(); secondaryPeer.start();
        if(!R7C6TestBridge.armCheckpoint(R7C6TestBridge.SOCKET_READ_ACTIVE,generation,111,5000))
            throw new IllegalStateException("Activity-destroy socket checkpoint arm failed");
        final boolean[] delivered={true,true};
        Thread primaryRead=new Thread(new Runnable(){public void run(){
            delivered[0]=R7C3TestBridge.receiveSocketFrame(receiver,generation,"127.0.0.1",
                    primaryServer.getLocalPort(),5000,110);
        }},"r7c7-activity-primary-reader");
        Thread secondaryRead=new Thread(new Runnable(){public void run(){
            delivered[1]=R7C3TestBridge.receiveSocketFrame(receiver,generation,"127.0.0.1",
                    secondaryServer.getLocalPort(),5000,111);
        }},"r7c7-activity-secondary-reader");
        activeSocketRace=true; primaryRead.start(); secondaryRead.start();
        if(!accepted.await(5,TimeUnit.SECONDS)||!R7C6TestBridge.waitForCheckpoint(
                R7C6TestBridge.SOCKET_READ_ACTIVE,generation,111,5000))
            throw new IllegalStateException("Activity-destroy read checkpoint missing");
        if(!R7C6TestBridge.resetForNextCase(5000))
            throw new IllegalStateException("Activity-destroy checkpoint waiter did not leave before finish");
        assertRaceIdle("activity-destroy-before-finish");
        final CountDownLatch heartbeat = new CountDownLatch(1);
        final CountDownLatch postSurfaceHeartbeat = new CountDownLatch(1);
        destructionHeartbeat=postSurfaceHeartbeat;
        runOnUiThread(new Runnable(){public void run(){
            record("ACTIVITY_DESTROY_REQUESTED");
            mainHandler.post(new Runnable(){public void run(){record("MAIN_LOOPER_HEARTBEAT");heartbeat.countDown();}});
            if(secondaryHost!=null)secondaryHost.close();
            finish();
        }});
        boolean heartbeatResponsive=heartbeat.await(5,TimeUnit.SECONDS);
        record("MAIN_LOOPER_HEARTBEAT_RESULT="+(heartbeatResponsive?"RESPONSIVE":"BLOCKED_OR_LIFECYCLE_OCCUPIED"));
        if(!activityDestroyed.await(15000,TimeUnit.MILLISECONDS)) {
            dumpFailureState("onDestroy timeout");
            throw new IllegalStateException("framework onDestroy callback missing");
        }
        boolean afterSurfaceResponsive=postSurfaceHeartbeat.await(5,TimeUnit.SECONDS);
        record("POST_SURFACE_MAIN_LOOPER_HEARTBEAT_RESULT="+(afterSurfaceResponsive?"RESPONSIVE":"LIFECYCLE_TRANSITION_OCCUPIED"));
        destructionHeartbeat=null;
        primaryRead.join(5000); secondaryRead.join(5000); primaryPeer.join(5000); secondaryPeer.join(5000);
        primaryServer.close(); secondaryServer.close(); activeSocketRace=false;
        if(primaryRead.isAlive()||secondaryRead.isAlive()||primaryPeer.isAlive()||secondaryPeer.isAlive()||
                delivered[0]||delivered[1]||activityDestroyAudio!=null||activityDestroyInput!=null)
            throw new IllegalStateException("Activity destruction did not release owned runtime adapters");
        requireNativeZero("Activity destroy race cleanup");
        assertRaceIdle("activity-destroy-after");
        record("ACTIVITY_DESTROY_DUAL_STREAM_RACE=PASS repeat="+getIntent().getIntExtra("r7c7Repeat",1));
    }

    private Thread waitForSocketClose(final ServerSocket server,final CountDownLatch accepted,final String name) {
        return new Thread(new Runnable(){public void run(){
            try{Socket socket=server.accept();accepted.countDown();while(socket.getInputStream().read()>=0){}socket.close();}
            catch(Throwable t){record("ACTIVITY_DESTROY_PEER_ERROR name="+name+" type="+t.getClass().getSimpleName());}
        }},name);
    }

    private void assertRaceIdle(String phase) {
        boolean idle=R7C6TestBridge.raceControllerIdle();
        record("RACE_CONTROLLER_STATE phase="+phase+" idle="+idle);
        if(!idle)throw new IllegalStateException("race controller not idle at "+phase);
    }

    private void dumpFailureState(String reason) {
        record("ACTIVITY_DESTROY_FAILURE="+reason+" native="+java.util.Arrays.toString(NativeBridge.nativeDebugResourceCounts())+
                " sockets="+R7C3TestBridge.openSocketDescriptorCount()+" raceIdle="+R7C6TestBridge.raceControllerIdle());
        Thread[] threads=new Thread[Thread.activeCount()*2+8];
        int count=Thread.enumerate(threads);
        for(int i=0;i<count;i++)if(threads[i]!=null){
            record("THREAD name="+threads[i].getName()+" state="+threads[i].getState()+
                    " daemon="+threads[i].isDaemon()+" id="+threads[i].getId());
            StackTraceElement[] stack=threads[i].getStackTrace();
            for(int frame=0;frame<Math.min(stack.length,12);frame++)record("THREAD_FRAME name="+
                    threads[i].getName()+" frame="+stack[frame].toString());
        }
    }

    private void runFrameworkPrimarySurfaceDestroyRace(final Surface primary, final byte[] h110)
            throws Exception {
        final Surface secondary = presentationSurface != null ? presentationSurface : fallbackSecondarySurface;
        if (primary == null || secondary == null) throw new IllegalStateException("primary race surfaces unavailable");
        final long generation=40410;
        final long p=NativeBridge.nativeAttachSurface(primary,generation,110,generation*2);
        final long s=NativeBridge.nativeAttachSurface(secondary,generation,111,generation*2+1);
        final long receiver=NativeBridge.nativeCreateReceiver(generation,p,s,true);
        if(!NativeBridge.nativeSetup(receiver,generation,1100,1101,true))
            throw new IllegalStateException("primary Surface race SETUP failed");
        activeRaceReceiver=receiver; activeRacePrimarySurface=p; activeRaceSecondarySurface=s;
        primarySurfaceDestroyed=new CountDownLatch(1);
        final int checkpoint=R7C6TestBridge.DECODE_PRIMARY_BEFORE_POST;
        if(!R7C6TestBridge.armCheckpoint(checkpoint,generation,110,5000))
            throw new IllegalStateException("could not arm primary Surface checkpoint");
        final boolean[] result={true}; final Throwable[] failure={null};
        Thread decode=new Thread(new Runnable(){public void run(){
            try { result[0]=NativeBridge.nativeTestIngestSyntheticPacket(receiver,generation,
                    packet(generation,110,1100,h110)); }
            catch(Throwable t){failure[0]=t;}
        }},"r7c6-primary-surface-race");
        decode.start();
        if(!R7C6TestBridge.waitForCheckpoint(checkpoint,generation,110,5000))
            throw new IllegalStateException("primary decoded frame did not reach pre-post checkpoint");
        runOnUiThread(new Runnable(){public void run(){rootView.removeView(primaryView);}});
        if(!primarySurfaceDestroyed.await(5,TimeUnit.SECONDS))
            throw new IllegalStateException("primary framework surfaceDestroyed callback missing");
        if(!R7C6TestBridge.releaseCheckpoint(checkpoint,generation,110))
            throw new IllegalStateException("primary Surface checkpoint release failed");
        decode.join(5000);
        if(decode.isAlive() || failure[0]!=null || result[0])
            throw new IllegalStateException("Type110 posted after framework Surface destruction");
        long[] counts=NativeBridge.nativeDebugResourceCounts();
        if(counts[4]!=0 || counts[5]!=0 || counts[1]!=1)
            throw new IllegalStateException("Type110 Surface loss did not close both streams and release primary owner");
        NativeBridge.nativeReleaseReceiver(receiver);
        NativeBridge.nativeReleaseSurface(s);
        activeRaceReceiver=0; activeRaceSecondarySurface=0;
        requireNativeZero("primary framework Surface race cleanup");
        R7C6TestBridge.clearCheckpoints();
        record("TYPE110_SURFACE_DESTROY_FRAME_RACE=PASS_SESSION_CLOSED");
        primarySurfaceCreated=new CountDownLatch(1);
        runOnUiThread(new Runnable(){public void run(){
            rootView.addView(primaryView,new FrameLayout.LayoutParams(640,480,Gravity.TOP|Gravity.LEFT));
        }});
        if(!primarySurfaceCreated.await(5,TimeUnit.SECONDS) || primarySurface==null)
            throw new IllegalStateException("primary Surface recreation failed after race");
    }

    private void runFrameworkSecondarySurfaceDestroyRace(final Surface primary, final byte[] h110,
                                                           final byte[] h111, final boolean dismiss)
            throws Exception {
        if (presentationSurface == null || secondaryHost == null)
            throw new IllegalStateException("framework secondary Surface/Presentation unavailable");
        final long generation = dismiss ? 40222 : 40221;
        final long p = NativeBridge.nativeAttachSurface(primary, generation, 110, generation * 2);
        final long s = NativeBridge.nativeAttachSurface(presentationSurface, generation, 111, generation * 2 + 1);
        final long receiver = NativeBridge.nativeCreateReceiver(generation, p, s, true);
        if (!NativeBridge.nativeSetup(receiver, generation, 1100, 1101, true))
            throw new IllegalStateException("framework Surface race SETUP failed");
        activeRaceReceiver = receiver;
        activeRacePrimarySurface = p;
        activeRaceSecondarySurface = s;
        secondarySurfaceDestroyed = new CountDownLatch(1);
        final int checkpoint = R7C6TestBridge.DECODE_SECONDARY_BEFORE_POST;
        if (!R7C6TestBridge.armCheckpoint(checkpoint, generation, 111, 5000))
            throw new IllegalStateException("could not arm framework Surface checkpoint");
        final boolean[] result = {true};
        final Throwable[] failure = {null};
        Thread decode = new Thread(new Runnable() { public void run() {
            try { result[0] = NativeBridge.nativeTestIngestSyntheticPacket(receiver, generation,
                    packet(generation, 111, 1101, h111)); }
            catch (Throwable t) { failure[0] = t; }
        }}, "r7c6-framework-surface-race");
        decode.start();
        if (!R7C6TestBridge.waitForCheckpoint(checkpoint, generation, 111, 5000))
            throw new IllegalStateException("decoded Type111 frame did not reach pre-post checkpoint");
        runOnUiThread(new Runnable() { public void run() {
            if (dismiss) secondaryHost.close();
            else if (!secondaryHost.destroySurfaceForRuntimeTest())
                record("FRAMEWORK_SURFACE_DESTROY_REQUEST_REJECTED");
        }});
        if (!secondarySurfaceDestroyed.await(20, TimeUnit.SECONDS))
            throw new IllegalStateException("framework surfaceDestroyed callback missing dismiss=" + dismiss);
        if (!R7C6TestBridge.releaseCheckpoint(checkpoint, generation, 111))
            throw new IllegalStateException("framework Surface checkpoint release failed");
        decode.join(5000);
        if (decode.isAlive() || failure[0] != null || result[0])
            throw new IllegalStateException("Type111 frame posted after framework Surface loss");
        if (activeRaceSecondarySurface != 0)
            throw new IllegalStateException("secondary Surface callback retained a native sink owner");
        long[] counts = NativeBridge.nativeDebugResourceCounts();
        if (counts[4] != 1 || counts[5] != 1)
            throw new IllegalStateException("Type111 framework Surface loss did not preserve only Type110");
        if (!NativeBridge.nativeTestIngestSyntheticPacket(receiver, generation,
                packet(generation, 110, 1100, h110)))
            throw new IllegalStateException("Type110 could not post after Type111 framework Surface loss");
        NativeBridge.nativeDisconnect(receiver);
        NativeBridge.nativeReleaseReceiver(receiver);
        NativeBridge.nativeReleaseSurface(p);
        activeRaceReceiver = 0;
        activeRacePrimarySurface = 0;
        requireNativeZero("framework Surface race cleanup");
        R7C6TestBridge.clearCheckpoints();
        record(dismiss ? "PRESENTATION_DISMISS_FRAME_RACE=PASS_TYPE110_RETAINED" :
                "TYPE111_SURFACE_DESTROY_FRAME_RACE=PASS_TYPE110_RETAINED");
        if (!dismiss) {
            secondarySurfaceCreated = new CountDownLatch(1);
            runOnUiThread(new Runnable() { public void run() {
                if (!secondaryHost.recreateSurfaceForRuntimeTest())
                    record("FRAMEWORK_SURFACE_RECREATE_REQUEST_REJECTED");
            }});
            if (!secondarySurfaceCreated.await(20, TimeUnit.SECONDS) || presentationSurface == null)
                throw new IllegalStateException("framework secondary Surface recreation failed");
        }
    }

    private void runSetupCancellationRace(Surface primary, byte[] h264, final boolean secondary)
            throws Exception {
        final long generation = secondary ? 40112 : 40110;
        long p = NativeBridge.nativeAttachSurface(primary, generation, 110, generation * 2);
        long s = NativeBridge.nativeAttachSurface(presentationSurface != null ? presentationSurface : fallbackSecondarySurface,
                generation, 111, generation * 2 + 1);
        final long receiver = NativeBridge.nativeCreateReceiver(generation, p, s, true);
        if (secondary && !R7C6TestBridge.setupStream(receiver, generation, 110, 1100))
            throw new IllegalStateException("primary prerequisite for Type111 setup race failed");
        final int stream = secondary ? 111 : 110;
        final int checkpoint = secondary ? R7C6TestBridge.SETUP_SECONDARY_ALLOCATED :
                R7C6TestBridge.SETUP_PRIMARY_ALLOCATED;
        if (!R7C6TestBridge.armCheckpoint(checkpoint, generation, stream, 5000))
            throw new IllegalStateException("could not arm setup checkpoint");
        final boolean[] result = {true};
        final Throwable[] failure = {null};
        Thread setup = new Thread(new Runnable() { public void run() {
            try { result[0] = R7C6TestBridge.setupStream(receiver, generation, stream,
                    secondary ? 1101 : 1100); }
            catch (Throwable t) { failure[0] = t; }
        }}, "r7c6-setup-race-" + stream);
        setup.start();
        if (!R7C6TestBridge.waitForCheckpoint(checkpoint, generation, stream, 5000))
            throw new IllegalStateException("setup checkpoint was not reached stream=" + stream);
        R7C6TestBridge.requestReceiverClose(receiver, secondary ? 111 : 0);
        if (!R7C6TestBridge.releaseCheckpoint(checkpoint, generation, stream))
            throw new IllegalStateException("setup checkpoint release failed");
        setup.join(5000);
        if (setup.isAlive() || failure[0] != null || result[0])
            throw new IllegalStateException("setup cancellation did not roll back stream=" + stream);
        long[] counts = NativeBridge.nativeDebugResourceCounts();
        if (secondary && (counts[4] != 1 || counts[5] != 1))
            throw new IllegalStateException("Type111 setup rollback did not preserve Type110");
        if (!secondary && (counts[4] != 0 || counts[5] != 0))
            throw new IllegalStateException("Type110 setup rollback retained a stream");
        if (!secondary) NativeBridge.nativeDisconnect(receiver);
        NativeBridge.nativeReleaseReceiver(receiver);
        NativeBridge.nativeReleaseSurface(p);
        NativeBridge.nativeReleaseSurface(s);
        requireNativeZero("setup race cleanup");
        R7C6TestBridge.clearCheckpoints();
        record("SETUP_CANCEL_RACE stream=" + stream + " rollback=PASS");
    }

    private void runDecodeCancellationRace(Surface primary, byte[] h110, byte[] h111,
                                           final int stream) throws Exception {
        final long generation = 40200 + stream;
        long p = NativeBridge.nativeAttachSurface(primary, generation, 110, generation * 2);
        long s = NativeBridge.nativeAttachSurface(presentationSurface != null ? presentationSurface : fallbackSecondarySurface,
                generation, 111, generation * 2 + 1);
        final long receiver = NativeBridge.nativeCreateReceiver(generation, p, s, true);
        if (!NativeBridge.nativeSetup(receiver, generation, 1100, 1101, true))
            throw new IllegalStateException("decode race SETUP failed");
        final int checkpoint = stream == 110 ? R7C6TestBridge.DECODE_PRIMARY_BEFORE_POST :
                R7C6TestBridge.DECODE_SECONDARY_BEFORE_POST;
        final int connection = stream == 110 ? 1100 : 1101;
        final byte[] media = stream == 110 ? h110 : h111;
        final byte[] framed = packet(generation, stream, connection, media);
        if (!R7C6TestBridge.armCheckpoint(checkpoint, generation, stream, 5000))
            throw new IllegalStateException("could not arm decode checkpoint");
        final boolean[] result = {true};
        final Throwable[] failure = {null};
        Thread decode = new Thread(new Runnable() { public void run() {
            try { result[0] = NativeBridge.nativeTestIngestSyntheticPacket(receiver, generation, framed); }
            catch (Throwable t) { failure[0] = t; }
        }}, "r7c6-decode-race-" + stream);
        decode.start();
        if (!R7C6TestBridge.waitForCheckpoint(checkpoint, generation, stream, 5000))
            throw new IllegalStateException("decode checkpoint was not reached stream=" + stream);
        R7C6TestBridge.requestReceiverClose(receiver, stream == 110 ? 0 : 111);
        if (!R7C6TestBridge.releaseCheckpoint(checkpoint, generation, stream))
            throw new IllegalStateException("decode checkpoint release failed");
        decode.join(5000);
        if (decode.isAlive() || failure[0] != null || result[0])
            throw new IllegalStateException("decode cancellation failed stream=" + stream);
        long[] counts = NativeBridge.nativeDebugResourceCounts();
        if (stream == 111) {
            if (counts[4] != 1 || counts[5] != 1)
                throw new IllegalStateException("Type111 decode cancellation did not preserve Type110");
            byte[] primaryFrame = packet(generation, 110, 1100, h110);
            if (!NativeBridge.nativeTestIngestSyntheticPacket(receiver, generation, primaryFrame))
                throw new IllegalStateException("Type110 failed after Type111 decode cancellation");
        } else if (counts[4] != 0 || counts[5] != 0) {
            throw new IllegalStateException("Type110 decode cancellation did not close both streams");
        }
        NativeBridge.nativeDisconnect(receiver);
        NativeBridge.nativeReleaseReceiver(receiver);
        NativeBridge.nativeReleaseSurface(p);
        NativeBridge.nativeReleaseSurface(s);
        requireNativeZero("decode race cleanup");
        R7C6TestBridge.clearCheckpoints();
        record("DECODE_CANCEL_RACE stream=" + stream + " cleanup=PASS");
    }

    private void runNativeSocketReadShutdownRace() throws Exception {
        final long generation = 40310;
        long p = NativeBridge.nativeAttachSurface(primarySurface, generation, 110, 403100);
        long s = NativeBridge.nativeAttachSurface(presentationSurface != null ? presentationSurface : fallbackSecondarySurface,
                generation, 111, 403101);
        final long receiver = NativeBridge.nativeCreateReceiver(generation, p, s, true);
        if (!NativeBridge.nativeSetup(receiver, generation, 1100, 1101, true))
            throw new IllegalStateException("socket read race SETUP failed");
        final ServerSocket server = new ServerSocket(0, 1, java.net.InetAddress.getByName("127.0.0.1"));
        final CountDownLatch accepted = new CountDownLatch(1);
        final Throwable[] peerFailure = {null};
        Thread peer = new Thread(new Runnable() { public void run() {
            try { Socket socket = server.accept(); accepted.countDown();
                while (socket.getInputStream().read() >= 0) { }
                socket.close();
            } catch (Throwable t) { peerFailure[0] = t; }
        }}, "r7c6-read-peer");
        peer.start();
        if (!R7C6TestBridge.armCheckpoint(R7C6TestBridge.SOCKET_READ_ACTIVE, generation, 111, 5000))
            throw new IllegalStateException("could not arm socket read checkpoint");
        final boolean[] result = {true};
        Thread reader = new Thread(new Runnable() { public void run() {
            try { result[0] = R7C3TestBridge.receiveSocketFrame(receiver, generation, "127.0.0.1",
                    server.getLocalPort(), 5000, 111); }
            catch (Throwable t) { peerFailure[0] = t; }
        }}, "r7c6-native-reader");
        reader.start();
        record("SOCKET_READ_PROBE_STARTED");
        if (!accepted.await(5, TimeUnit.SECONDS) || !R7C6TestBridge.waitForCheckpoint(
                R7C6TestBridge.SOCKET_READ_ACTIVE, generation, 111, 5000))
            throw new IllegalStateException("native adapter did not reach active read");
        record("SOCKET_READ_CHECKPOINT_REACHED");
        R7C6TestBridge.shutdownActiveSocket();
        record("SOCKET_READ_SHUTDOWN_REQUESTED");
        R7C6TestBridge.releaseCheckpoint(R7C6TestBridge.SOCKET_READ_ACTIVE, generation, 111);
        reader.join(5000); server.close(); peer.join(5000);
        if (reader.isAlive() || peer.isAlive() || result[0] || peerFailure[0] != null)
            throw new IllegalStateException("native socket read shutdown did not terminate cleanly");
        record("SOCKET_READ_THREADS_JOINED");
        NativeBridge.nativeReleaseReceiver(receiver);
        NativeBridge.nativeReleaseSurface(p); NativeBridge.nativeReleaseSurface(s);
        requireNativeZero("socket read race cleanup");
        R7C6TestBridge.clearCheckpoints();
        record("NATIVE_SOCKET_READ_SHUTDOWN_RACE=PASS");
    }

    private void runNativeSocketWriteShutdownRace() throws Exception {
        final long generation = 40311;
        final ServerSocket server = new ServerSocket(0, 1, java.net.InetAddress.getByName("127.0.0.1"));
        final CountDownLatch accepted = new CountDownLatch(1);
        final Throwable[] peerFailure = {null};
        Thread peer = new Thread(new Runnable() { public void run() {
            try { Socket socket = server.accept(); accepted.countDown();
                while (socket.getInputStream().read() >= 0) { }
                socket.close();
            } catch (Throwable t) { peerFailure[0] = t; }
        }}, "r7c6-write-peer");
        peer.start();
        if (!R7C6TestBridge.armCheckpoint(R7C6TestBridge.SOCKET_WRITE_ACTIVE, generation, 111, 5000))
            throw new IllegalStateException("could not arm socket write checkpoint");
        final int[] result = {1};
        final byte[] data = new byte[65536];
        Thread writer = new Thread(new Runnable() { public void run() {
            result[0] = R7C6TestBridge.connectAndWrite("127.0.0.1", server.getLocalPort(),
                    generation, 111, data, 5000);
        }}, "r7c6-native-writer");
        writer.start();
        if (!accepted.await(5, TimeUnit.SECONDS) || !R7C6TestBridge.waitForCheckpoint(
                R7C6TestBridge.SOCKET_WRITE_ACTIVE, generation, 111, 5000))
            throw new IllegalStateException("native adapter did not reach active write");
        R7C6TestBridge.shutdownActiveSocket();
        R7C6TestBridge.releaseCheckpoint(R7C6TestBridge.SOCKET_WRITE_ACTIVE, generation, 111);
        writer.join(5000); server.close(); peer.join(5000);
        if (writer.isAlive() || peer.isAlive() || result[0] >= 0 || peerFailure[0] != null)
            throw new IllegalStateException("native socket write shutdown did not terminate cleanly");
        R7C6TestBridge.clearCheckpoints();
        record("NATIVE_SOCKET_WRITE_SHUTDOWN_RACE=PASS");
    }

    private void enumerateDisplays() {
        try {
            List<DisplayDiscovery.Info> displays=new DisplayDiscovery(this).enumerate();
            StringBuilder line=new StringBuilder("DISPLAY_COUNT=").append(displays.size());
            for(DisplayDiscovery.Info d:displays) line.append(" id=").append(d.id).append(':').append(d.width).append('x').append(d.height).append('/').append(d.valid);
            record(line.toString());
            DisplayManager manager=(DisplayManager)getSystemService(Context.DISPLAY_SERVICE);
            Display secondary=null;
            for(Display d:manager.getDisplays()) if(d!=null && d.isValid() && d.getDisplayId()!=0) { if(secondary!=null) { secondary=null; break; } secondary=d; }
            if(secondary!=null) {
                secondaryDisplay=secondary;
                secondaryHost=new SecondaryDisplayHost(new SecondaryDisplayHost.Listener() {
                    public void state(DisplayPolicy.Admission state) { record("PRESENTATION_STATE="+state.name()); }
                    public void surface(Surface surface) {
                        synchronized(surfaceLock) { presentationSurface=surface; }
                        if(surface==null) {
                            record("SECONDARY_SURFACE_DESTROYED");
                            long handle=activeRaceSecondarySurface; activeRaceSecondarySurface=0;
                            if(handle>0) { NativeBridge.nativeReleaseSurface(handle); record("SECONDARY_SINK_INVALIDATED"); }
                            CountDownLatch destroyed=secondarySurfaceDestroyed;
                            if(destroyed!=null) destroyed.countDown();
                        } else {
                            CountDownLatch created=secondarySurfaceCreated;
                            if(created!=null) created.countDown();
                        }
                        maybeStart();
                    }
                    public void error(String op,String type) { record("PRESENTATION_ERROR="+op+":"+type); }
                });
                boolean shown=secondaryHost.showOfflineLabForRuntimeTest(this,secondary,1001,
                        DisplayPolicy.FULL_FRAME_TEST_LAYOUT);
                record("PRESENTATION_LAB_SHOWN="+shown+" displayId="+secondary.getDisplayId());
            } else record("SECONDARY_DISPLAY=ABSENT_OR_AMBIGUOUS");
        } catch(RuntimeException e) { runtimeFailure="display:"+e.getClass().getName(); record("DISPLAY_EXCEPTION="+e.getClass().getName()); }
    }

    private void maybeStart() {
        final Surface p, s;
        synchronized(surfaceLock) {
            if(started || primarySurface==null) return;
            s=presentationSurface!=null?presentationSurface:fallbackSecondarySurface;
            if(s==null) return;
            started=true; p=primarySurface;
        }
        new Thread(new Runnable() { public void run() { runIntegration(p,s); } },"r7c2-integrated-test").start();
    }

    private void runIntegration(Surface primary,Surface secondary) {
        int cycles=0; boolean allFrames=true; String error=runtimeFailure;
        String focusedCase=getIntent().getStringExtra("r7c6Case");
        activeTestCase=focusedCase==null?"combined":focusedCase;
        if("socket-read".equals(focusedCase) || "socket-read-after-dismiss".equals(focusedCase) ||
                "primary-surface".equals(focusedCase) || "activity-destroy".equals(focusedCase)) {
            try {
                if("activity-destroy".equals(focusedCase)) {
                    runActivityDestroyDuringDualStream(primary,fixture("type110-red.h264.b64"),fixture("type111-blue.h264.b64"));
                    saveResult(0,null);
                    runOnUiThread(new Runnable() { public void run() { finish(); } });
                    return;
                }
                if("primary-surface".equals(focusedCase)) {
                    runFrameworkPrimarySurfaceDestroyRace(primary,fixture("type110-red.h264.b64"));
                }
                if("socket-read-after-dismiss".equals(focusedCase)) {
                    byte[] primaryFixture=fixture("type110-red.h264.b64");
                    byte[] secondaryFixture=fixture("type111-blue.h264.b64");
                    runFrameworkSecondarySurfaceDestroyRace(primary, primaryFixture, secondaryFixture, false);
                    runFrameworkSecondarySurfaceDestroyRace(primary, primaryFixture, secondaryFixture, true);
                }
                runNativeSocketReadShutdownRace();
            }
            catch(Throwable t) { error=t.getClass().getName()+":"+String.valueOf(t.getMessage()); Log.e(TAG,"focused socket-read case failed",t); }
            saveResult(0,error);
            runOnUiThread(new Runnable() { public void run() { finish(); } });
            return;
        }
        boolean invalidSurfaceRejected=false;
        try { NativeBridge.nativeAttachSurface(null,1,110,1); }
        catch(IllegalStateException expected) { invalidSurfaceRejected=true; }
        if(!invalidSurfaceRejected) {
            saveResult(0,"JNI accepted a null Surface");
            runOnUiThread(new Runnable() { public void run() { finish(); } });
            return;
        }
        record("JNI_INVALID_SURFACE=REJECTED");
        try {
            int adapterChecks=runNonVideoAdapters();
            record("ADAPTER_CHECKS="+adapterChecks);
            byte[] h110=fixture("type110-red.h264.b64");
            byte[] h111=fixture("type111-blue.h264.b64");
            exerciseNativeSocketReceiver(primary,secondary,h110,h111);
            runNativeSocketFaultMatrix(primary,secondary,h110,h111);
            exerciseJniExceptionSeams();
            recordMemory("baseline",0);
            for(int cycle=0;cycle<100;cycle++) {
                long generation=20000L+cycle;
                int fdBeforeCycle=R7C3TestBridge.openSocketDescriptorCount();
                long oldPrimary=NativeBridge.nativeAttachSurface(primary,generation,110,generation*2);
                NativeBridge.nativeReleaseSurface(oldPrimary);
                long p=NativeBridge.nativeAttachSurface(primary,generation,110,generation*2+100000);
                long s=NativeBridge.nativeAttachSurface(secondary,generation,111,generation*2+1);
                if(p<=0 || s<=0) throw new IllegalStateException("surface attach did not return validated handles");
                boolean productionRejected=false;
                try { NativeBridge.nativeCreateReceiver(generation,p,s,false); }
                catch(IllegalStateException expected) { productionRejected=true; }
                if(!productionRejected) throw new IllegalStateException("production authority unexpectedly accepted");
                long receiver=NativeBridge.nativeCreateReceiver(generation,p,s,true);
                if(receiver<=0 || !NativeBridge.nativeSetup(receiver,generation,1100,1101,true))
                    throw new IllegalStateException("LAB receiver / SETUP path failed");
                long[] active=NativeBridge.nativeDebugResourceCounts();
                if(active.length!=8 || active[0]!=1 || active[1]!=2 || active[4]!=2 || active[5]!=2)
                    throw new IllegalStateException("active native ownership counters not dual-stream");
                int cycleAdapterChecks=runNonVideoAdapters();
                if(cycleAdapterChecks<6) throw new IllegalStateException("per-cycle audio/input/USB/auth lifecycle incomplete");
                boolean frame110=deliverFragmentedSocketFrame(receiver,generation,110,1100,h110);
                boolean frame111=deliverFragmentedSocketFrame(receiver,generation,111,1101,h111);
                if(!frame110 || !frame111) allFrames=false;
                NativeBridge.nativeDisconnect(receiver);
                NativeBridge.nativeReleaseReceiver(receiver);
                NativeBridge.nativeReleaseSurface(p);
                NativeBridge.nativeReleaseSurface(s);
                boolean staleRejected=false;
                try { NativeBridge.nativeDisconnect(receiver); } catch(IllegalStateException expected) { staleRejected=true; }
                if(!staleRejected) throw new IllegalStateException("stale JNI handle accepted");
                long[] closed=NativeBridge.nativeDebugResourceCounts();
                for(int i=0;i<closed.length;i++) if(closed[i]!=0) throw new IllegalStateException("native owner leaked counter="+i+" cycle="+cycle);
                int fdAfterCycle=R7C3TestBridge.openSocketDescriptorCount();
                if(fdAfterCycle!=fdBeforeCycle) throw new IllegalStateException("native socket FD count changed cycle="+cycle+" before="+fdBeforeCycle+" after="+fdAfterCycle);
                cycles++;
                if(cycles==1) recordMemory("post-warmup",cycles);
                if(cycles%10==0) recordMemory("cycle",cycles);
            }
            if(!allFrames) throw new IllegalStateException("generation/stream guard or H.264 Surface post failed");
            record("TYPE110_H264_ANDROID_SURFACE=PASS");
            record("TYPE111_H264_ANDROID_SURFACE=PASS");
            injectType111SurfaceLoss(primary,secondary);
            injectPrimarySurfaceLoss(primary,secondary);
            runDeterministicRaceSuite(primary,h110,h111);
            System.gc(); recordMemory("after-gc",cycles);
            record("JNI_STALE_HANDLE=REJECTED");
        } catch(Throwable t) {
            error=t.getClass().getName()+":"+String.valueOf(t.getMessage());
            Log.e(TAG,"runtime integration failed",t);
        } finally {
            if(secondaryHost!=null) runOnUiThread(new Runnable() { public void run() { secondaryHost.close(); } });
            String finalError=error;
            saveResult(cycles,finalError);
            runOnUiThread(new Runnable() { public void run() { finish(); } });
        }
    }

    private void injectType111SurfaceLoss(Surface primary,Surface secondary) throws Exception {
        long generation=30110;
        byte[] h110=fixture("type110-red.h264.b64"), h111=fixture("type111-blue.h264.b64");
        long p=NativeBridge.nativeAttachSurface(primary,generation,110,7001);
        long s=NativeBridge.nativeAttachSurface(secondary,generation,111,7002);
        long receiver=NativeBridge.nativeCreateReceiver(generation,p,s,true);
        if(!NativeBridge.nativeSetup(receiver,generation,1100,1101,true)) throw new IllegalStateException("Type111 fault SETUP failed");
        NativeBridge.nativeReleaseSurface(s); // Invalidates only the secondary native sink.
        boolean primaryBefore=NativeBridge.nativeTestIngestSyntheticPacket(receiver,generation,packet(generation,110,1100,h110));
        boolean secondaryDelivered=NativeBridge.nativeTestIngestSyntheticPacket(receiver,generation,packet(generation,111,1101,h111));
        long[] isolated=NativeBridge.nativeDebugResourceCounts();
        boolean primaryAfter=NativeBridge.nativeTestIngestSyntheticPacket(receiver,generation,packet(generation,110,1100,h110));
        if(!primaryBefore || secondaryDelivered || !primaryAfter || isolated[0]!=1 || isolated[1]!=1 || isolated[5]!=1)
            throw new IllegalStateException("Type111 native surface loss was not isolated from Type110");
        NativeBridge.nativeDisconnect(receiver); NativeBridge.nativeReleaseReceiver(receiver); NativeBridge.nativeReleaseSurface(p);
        requireNativeZero("Type111 surface-loss cleanup");
        record("TYPE111_SURFACE_LOSS=STREAM_LOCAL_TYPE110_RETAINED");
    }

    private void injectPrimarySurfaceLoss(Surface primary,Surface secondary) throws Exception {
        long generation=30111;
        byte[] h110=fixture("type110-red.h264.b64");
        long p=NativeBridge.nativeAttachSurface(primary,generation,110,7101);
        long s=NativeBridge.nativeAttachSurface(secondary,generation,111,7102);
        long receiver=NativeBridge.nativeCreateReceiver(generation,p,s,true);
        if(!NativeBridge.nativeSetup(receiver,generation,1100,1101,true)) throw new IllegalStateException("primary-fault SETUP failed");
        NativeBridge.nativeReleaseSurface(p);
        boolean primaryDelivered=NativeBridge.nativeTestIngestSyntheticPacket(receiver,generation,packet(generation,110,1100,h110));
        long[] closed=NativeBridge.nativeDebugResourceCounts();
        if(primaryDelivered || closed[0]!=1 || closed[1]!=1 || closed[4]!=0 || closed[5]!=0)
            throw new IllegalStateException("Type110 failure did not close session streams");
        NativeBridge.nativeDisconnect(receiver); NativeBridge.nativeReleaseReceiver(receiver); NativeBridge.nativeReleaseSurface(s);
        requireNativeZero("Type110 session-global cleanup");
        record("TYPE110_SURFACE_LOSS=SESSION_GLOBAL_CLOSED");
    }

    private static void requireNativeZero(String operation) {
        long[] counts=NativeBridge.nativeDebugResourceCounts();
        for(int i=0;i<counts.length;i++) if(counts[i]!=0)
            throw new IllegalStateException(operation+" retained native counter="+i);
    }

    private void recordMemory(String phase,int cycle) {
        record("MEMORY phase="+phase+" cycle="+cycle+" pssKb="+Debug.getPss()+
                " nativeHeapAllocatedBytes="+Debug.getNativeHeapAllocatedSize());
    }

    private int runNonVideoAdapters() throws Exception {
        int checks=0;
        Set<String> allow=new HashSet<String>(); allow.add("TOUCH:1:7");
        InputBridge input=new InputBridge(allow);
        if(!input.accept(new InputBridge.Event(1,InputBridge.Kind.TOUCH,7,1,1,55),55) ||
           input.accept(new InputBridge.Event(1,InputBridge.Kind.STEERING,999,1,2,55),55) ||
           input.accept(new InputBridge.Event(1,InputBridge.Kind.TOUCH,7,1,3,56),55)) throw new IllegalStateException("input allowlist/generation check failed");
        checks++;
        SessionBoundaries.Iap2Transport iap2=new SessionBoundaries.UnavailableIap2();
        SessionBoundaries.AuthenticationAuthority authority=SessionBoundaries.AndroidAuthenticationAdapter.unavailableHondaDefault();
        if(iap2.ready() || authority.authenticate(55) || authority.genuineAuthority() || new MediaTransports.CarPlayMediaTransport().ready())
            throw new IllegalStateException("production transport/authentication must fail closed");
        checks++;
        AndroidUsbTransport usb=new AndroidUsbTransport(this);
        Map<String,android.hardware.usb.UsbDevice> devices=usb.discover();
        if(!devices.isEmpty()) throw new IllegalStateException("unexpected physical USB device in emulator-only test");
        usb.close(); record("USB_MANAGER=READY devices="+devices.size()); checks++;
        AndroidAudioAdapter audio=new AndroidAudioAdapter(this);
        if(audio.open(44100,2,AudioFormat.ENCODING_PCM_16BIT)) {
            byte[] pcm=new byte[4096];
            if(audio.write(pcm,0,pcm.length)<0) throw new IllegalStateException("AudioTrack bounded PCM write failed");
            audio.pause(); audio.resume(); audio.flush(); audio.close(); audio.close();
            record("AUDIOTRACK=OPEN_WRITE_PAUSE_RESUME_FLUSH_CLOSE");
        } else record("AUDIOTRACK=UNAVAILABLE error="+audio.errorState());
        checks++;
        exerciseLoopback(); checks++;
        final boolean[] active={false};
        ProcessLifecycleAdapter lifecycle=new ProcessLifecycleAdapter();
        ProcessLifecycleAdapter.Receiver receiver=new ProcessLifecycleAdapter.Receiver() {
            public boolean start() { active[0]=true; return true; }
            public void disconnect() { active[0]=false; }
            public void stop() { active[0]=false; }
            public boolean active() { return active[0]; }
        };
        if(!lifecycle.start(receiver) || !lifecycle.activate()) throw new IllegalStateException("process lifecycle start failed");
        lifecycle.own(new ProcessLifecycleAdapter.OwnedResource() {
            public String name() { return "test-owned"; }
            public boolean closeAndVerify() { return true; }
        });
        if(!lifecycle.stop(receiver) || lifecycle.state()!=ProcessLifecycleAdapter.State.STOPPED || active[0])
            throw new IllegalStateException("process lifecycle restoration failed");
        checks++;
        return checks;
    }

    private static void exerciseLoopback() throws Exception {
        final ServerSocket server=new ServerSocket(0,1,java.net.InetAddress.getByName("127.0.0.1"));
        server.setSoTimeout(3000);
        final CountDownLatch served=new CountDownLatch(1);
        final Throwable[] failure=new Throwable[1];
        Thread t=new Thread(new Runnable() { public void run() {
            try { Socket s=server.accept(); s.setSoTimeout(3000); int v=s.getInputStream().read(); if(v!=0x5a) throw new IllegalStateException("loopback payload mismatch"); s.getOutputStream().write(new byte[]{1,2,3}); s.close(); }
            catch(Throwable e) { failure[0]=e; } finally { served.countDown(); }
        }},"r7c2-loopback");
        t.start(); Socket client=new Socket("127.0.0.1",server.getLocalPort()); client.setSoTimeout(3000);
        client.getOutputStream().write(0x5a); byte[] response=new byte[3]; int n=client.getInputStream().read(response); client.close(); server.close();
        if(n!=3 || response[0]!=1 || response[2]!=3 || !served.await(3,TimeUnit.SECONDS) || failure[0]!=null)
            throw new IllegalStateException("bounded emulator loopback test failed");
    }

    private void exerciseNativeSocketReceiver(Surface primary, Surface secondary, byte[] h264, byte[] h264Secondary) throws Exception {
        final long generation=30200;
        long p=NativeBridge.nativeAttachSurface(primary,generation,110,8101);
        long s=NativeBridge.nativeAttachSurface(secondary,generation,111,8102);
        long receiver=NativeBridge.nativeCreateReceiver(generation,p,s,true);
        if(!NativeBridge.nativeSetup(receiver,generation,1100,1101,true)) throw new IllegalStateException("socket receiver SETUP failed");
        int fdBefore=R7C3TestBridge.openSocketDescriptorCount();
        boolean primaryFrame=deliverFragmentedSocketFrame(receiver,generation,110,1100,h264);
        boolean secondaryFrame=deliverFragmentedSocketFrame(receiver,generation,111,1101,h264Secondary);
        if(!primaryFrame || !secondaryFrame) throw new IllegalStateException("native socket LAB frame did not reach both ReceiverGeneration streams");
        record("R7C3_SOCKET_TYPE110_TYPE111_DUAL_SURFACES=PASS");
        NativeBridge.nativeDisconnect(receiver); record("R7C3_SOCKET_DISCONNECTED");
        NativeBridge.nativeReleaseReceiver(receiver); record("R7C3_SOCKET_RECEIVER_RELEASED");
        NativeBridge.nativeReleaseSurface(p); record("R7C3_SOCKET_PRIMARY_RELEASED");
        NativeBridge.nativeReleaseSurface(s); record("R7C3_SOCKET_SECONDARY_RELEASED");
        requireNativeZero("native socket receiver cleanup");
        int fdAfter=R7C3TestBridge.openSocketDescriptorCount();
        if(fdAfter!=fdBefore) throw new IllegalStateException("socket descriptor set did not return to baseline: before="+fdBefore+" after="+fdAfter);
        record("NATIVE_POSIX_SOCKET_JNI_RECEIVER=PASS protocol=LAB_LOOPBACK fdBefore="+fdBefore+" fdAfter="+fdAfter);
    }

    private void runNativeSocketFaultMatrix(Surface primary,Surface secondary,byte[] h110,byte[] h111)throws Exception{
        long generation=30300;
        runType111SocketFault("timeout",primary,secondary,generation,null,0,true,h110); generation++;
        runType111SocketFault("peer-close",primary,secondary,generation,null,0,false,h110); generation++;
        runType111SocketFault("malformed",primary,secondary,generation,badTypeFrame(generation,111,1101),0,false,h110); generation++;
        runType111SocketFault("truncated-header",primary,secondary,generation,new byte[]{1,2,3,4},0,false,h110); generation++;
        runType111SocketFault("truncated-payload",primary,secondary,generation,concat(socketHeader(generation,111,1101,100),new byte[]{7,8}),0,false,h110); generation++;
        runType111SocketFault("zero-payload",primary,secondary,generation,socketHeader(generation,111,1101,0),0,false,h110); generation++;
        runType111SocketFault("oversized",primary,secondary,generation,socketHeader(generation,111,1101,2*1024*1024+1),0,false,h110); generation++;
        runType111SocketFault("wrong-stream",primary,secondary,generation,packet(generation,110,1100,h110),0,false,h110); generation++;
        runType111SocketFault("wrong-generation",primary,secondary,generation,packet(generation-1,111,1101,h111),0,false,h110); generation++;
        runType111Refusal(primary,secondary,generation,h110); generation++;
        runType110SocketFailure(primary,secondary,generation);
        record("NATIVE_SOCKET_FAULT_MATRIX=PASS timeout refusal peer_close malformed truncated_header truncated_payload zero oversized wrong_stream wrong_generation type111_isolation type110_global");
        record("NATIVE_SOCKET_PORT_COLLISION=NOT_APPLICABLE adapter_is_client_only_and_binds_ephemeral_local_port");
    }

    private void runType111SocketFault(String name,Surface primary,Surface secondary,long generation,
            final byte[] wire,final int sendCount,final boolean holdOpen,byte[] h110)throws Exception{
        final long p=NativeBridge.nativeAttachSurface(primary,generation,110,generation*2);
        final long s=NativeBridge.nativeAttachSurface(secondary,generation,111,generation*2+1);
        final long receiver=NativeBridge.nativeCreateReceiver(generation,p,s,true);
        if(!NativeBridge.nativeSetup(receiver,generation,1100,1101,true))throw new IllegalStateException(name+" SETUP failed");
        int fdBefore=R7C3TestBridge.openSocketDescriptorCount();
        final ServerSocket server=new ServerSocket(0,1,java.net.InetAddress.getByName("127.0.0.1"));
        server.setSoTimeout(5000);
        final Throwable[] peerFailure={null};
        Thread peer=new Thread(new Runnable(){public void run(){
            try{
                Socket socket=server.accept();
                if(wire!=null){OutputStream out=socket.getOutputStream();int count=sendCount<=0?wire.length:Math.min(sendCount,wire.length);out.write(wire,0,count);out.flush();socket.shutdownOutput();}
                else if(holdOpen){while(socket.getInputStream().read()>=0){}}
                socket.close();
            }catch(Throwable t){peerFailure[0]=t;}
        }},"r7c7-socket-fault-"+name);
        peer.start();
        boolean delivered=R7C3TestBridge.receiveSocketFrame(receiver,generation,"127.0.0.1",server.getLocalPort(),
                holdOpen?1500:3000,111);
        peer.join(5000);server.close();
        if(peer.isAlive()||peerFailure[0]!=null)throw new IllegalStateException(name+" peer did not finish cleanly");
        if(delivered)throw new IllegalStateException(name+" Type111 fault was accepted");
        long[] counts=NativeBridge.nativeDebugResourceCounts();
        if(counts[0]!=1||counts[4]!=1||counts[5]!=1)throw new IllegalStateException(name+" failure escaped Type111 scope: "+java.util.Arrays.toString(counts));
        NativeBridge.nativeClearSurface(s,generation);
        if(!deliverFragmentedSocketFrame(receiver,generation,110,1100,h110))throw new IllegalStateException(name+" fault interrupted Type110 follow-up socket frame");
        int fdAfter=R7C3TestBridge.openSocketDescriptorCount();
        if(fdAfter!=fdBefore)throw new IllegalStateException(name+" leaked socket descriptor before="+fdBefore+" after="+fdAfter);
        NativeBridge.nativeDisconnect(receiver);NativeBridge.nativeReleaseReceiver(receiver);
        NativeBridge.nativeReleaseSurface(p);NativeBridge.nativeReleaseSurface(s);requireNativeZero(name+" cleanup");
        record("SOCKET_FAULT="+name+" scope=TYPE111_LOCAL type110_followup=PASS fdZero=PASS");
    }

    private void runType111Refusal(Surface primary,Surface secondary,long generation,byte[] h110)throws Exception{
        ServerSocket probe=new ServerSocket(0,1,java.net.InetAddress.getByName("127.0.0.1"));
        int port=probe.getLocalPort();probe.close();
        long p=NativeBridge.nativeAttachSurface(primary,generation,110,generation*2);
        long s=NativeBridge.nativeAttachSurface(secondary,generation,111,generation*2+1);
        long receiver=NativeBridge.nativeCreateReceiver(generation,p,s,true);
        if(!NativeBridge.nativeSetup(receiver,generation,1100,1101,true))throw new IllegalStateException("refusal SETUP failed");
        boolean delivered=R7C3TestBridge.receiveSocketFrame(receiver,generation,"127.0.0.1",port,3000,111);
        long[] counts=NativeBridge.nativeDebugResourceCounts();
        if(delivered||counts[4]!=1||counts[5]!=1)throw new IllegalStateException("connection refusal did not remain Type111-local");
        if(!deliverFragmentedSocketFrame(receiver,generation,110,1100,h110))throw new IllegalStateException("Type110 failed after Type111 refusal");
        NativeBridge.nativeDisconnect(receiver);NativeBridge.nativeReleaseReceiver(receiver);
        NativeBridge.nativeReleaseSurface(p);NativeBridge.nativeReleaseSurface(s);requireNativeZero("refusal cleanup");
        record("SOCKET_FAULT=refusal scope=TYPE111_LOCAL type110_followup=PASS");
    }

    private void runType110SocketFailure(Surface primary,Surface secondary,long generation)throws Exception{
        long p=NativeBridge.nativeAttachSurface(primary,generation,110,generation*2);
        long s=NativeBridge.nativeAttachSurface(secondary,generation,111,generation*2+1);
        long receiver=NativeBridge.nativeCreateReceiver(generation,p,s,true);
        if(!NativeBridge.nativeSetup(receiver,generation,1100,1101,true))throw new IllegalStateException("Type110 failure SETUP failed");
        ServerSocket probe=new ServerSocket(0,1,java.net.InetAddress.getByName("127.0.0.1"));
        int port=probe.getLocalPort();probe.close();
        boolean delivered=R7C3TestBridge.receiveSocketFrame(receiver,generation,"127.0.0.1",port,3000,110);
        long[] counts=NativeBridge.nativeDebugResourceCounts();
        if(delivered||counts[4]!=0||counts[5]!=0)throw new IllegalStateException("Type110 transport fault did not close the session");
        NativeBridge.nativeReleaseReceiver(receiver);NativeBridge.nativeReleaseSurface(p);NativeBridge.nativeReleaseSurface(s);
        requireNativeZero("Type110 socket failure cleanup");
        record("SOCKET_FAULT=Type110-refusal scope=SESSION_GLOBAL");
    }

    private static byte[] socketHeader(long generation,int stream,int connection,int length){
        byte[] header=packet(generation,stream,connection,new byte[]{1});
        header[11]=(byte)(length>>>24);header[12]=(byte)(length>>>16);header[13]=(byte)(length>>>8);header[14]=(byte)length;
        return java.util.Arrays.copyOf(header,15);
    }

    private static byte[] badTypeFrame(long generation,int stream,int connection){
        byte[] frame=packet(generation,stream,connection,new byte[]{1});frame[8]=99;return frame;
    }

    private static byte[] concat(byte[] a,byte[] b){
        byte[] joined=java.util.Arrays.copyOf(a,a.length+b.length);System.arraycopy(b,0,joined,a.length,b.length);return joined;
    }

    private boolean deliverFragmentedSocketFrame(final long receiver, final long generation,
            final int stream, final int connection, final byte[] h264) throws Exception {
        final byte[] frame=packet(generation,stream,connection,h264);
        final ServerSocket server=new ServerSocket(0,1,java.net.InetAddress.getByName("127.0.0.1"));
        server.setSoTimeout(3000);
        final Throwable[] peerFailure=new Throwable[1];
        Thread peer=new Thread(new Runnable() { public void run() {
            try {
                Socket accepted=server.accept(); accepted.setSoTimeout(3000);
                OutputStream out=accepted.getOutputStream();
                // Fragment the envelope/body to exercise adapter exact reads.
                for(int i=0;i<frame.length;i+=37) { int n=Math.min(37,frame.length-i); out.write(frame,i,n); out.flush(); }
                accepted.shutdownOutput(); accepted.close();
            } catch(Throwable t) { peerFailure[0]=t; }
        }},"r7c3-native-socket-peer-"+stream);
        peer.start();
        boolean accepted=R7C3TestBridge.receiveSocketFrame(receiver,generation,"127.0.0.1",server.getLocalPort(),3000,stream);
        peer.join(4000);
        server.close();
        record("R7C3_SOCKET_STREAM="+stream+" JNI_RETURN="+accepted+" PEER_JOINED="+(!peer.isAlive()));
        if(peer.isAlive() || peerFailure[0]!=null) throw new IllegalStateException("native socket peer failed for stream="+stream);
        return accepted;
    }

    private void exerciseJniExceptionSeams() {
        boolean pending=false;
        try { R7C3TestBridge.pendingExceptionProbe(); }
        catch(IllegalArgumentException expected) { pending=expected.getMessage().contains("R7C3 pending-exception probe"); }
        if(!pending) throw new IllegalStateException("JNI-created pending exception was not preserved");
        boolean lookup=false;
        try { R7C3TestBridge.lookupFailureProbe(); }
        catch(Throwable expected) {
            lookup=expected instanceof ClassNotFoundException || expected instanceof NoClassDefFoundError;
            record("JNI_LOOKUP_EXCEPTION_TYPE="+expected.getClass().getName());
        }
        if(!lookup) throw new IllegalStateException("JNI lookup exception was not preserved");
        record("JNI_PENDING_EXCEPTION=PASS JNI_LOOKUP_FAILURE=PASS");
    }

    private byte[] fixture(String name) throws Exception {
        InputStream in=getAssets().open(name); ByteArrayOutputStream out=new ByteArrayOutputStream(); byte[] b=new byte[1024]; int n;
        while((n=in.read(b))!=-1) { if(out.size()+n>16384) throw new IllegalStateException("fixture limit exceeded"); out.write(b,0,n); }
        in.close(); return Base64.decode(out.toByteArray(),Base64.DEFAULT);
    }
    private static byte[] packet(long generation,int type,int connection,byte[] payload) {
        byte[] out=new byte[15+payload.length];
        for(int i=0;i<8;i++) out[i]=(byte)(generation >>> (56-8*i));
        out[8]=(byte)type; out[9]=(byte)(connection>>>8); out[10]=(byte)connection;
        int n=payload.length; out[11]=(byte)(n>>>24); out[12]=(byte)(n>>>16); out[13]=(byte)(n>>>8); out[14]=(byte)n;
        System.arraycopy(payload,0,out,15,n); return out;
    }
    private void record(String line) {
        Log.i(TAG,"TRACE t="+SystemClock.elapsedRealtimeNanos()+" tid="+Thread.currentThread().getId()+
                " thread="+Thread.currentThread().getName()+" activity="+activityGeneration+
                " case="+activeTestCase+" event="+line);
    }
    private void saveResult(int cycles,String error) {
        String result=(error==null?"RESULT=PASS":"RESULT=FAIL")+"\nCYCLES="+cycles+"\nERROR="+(error==null?"NONE":error)+"\nRUNTIME="+System.getProperty("java.vm.name")+"\nAPI="+android.os.Build.VERSION.SDK_INT+"\n";
        try { FileOutputStream out=openFileOutput("r7c2-result.txt",MODE_PRIVATE); out.write(result.getBytes("UTF-8")); out.close(); }
        catch(Exception e) { Log.e(TAG,"result write failed",e); }
        Log.i(TAG,result);
    }
    protected void onPause() { record("ACTIVITY_PAUSED"); super.onPause(); }
    protected void onStop() { record("ACTIVITY_STOPPED"); super.onStop(); }
    protected void onResume() { super.onResume(); record("ACTIVITY_RESUMED"); }
    protected void onDestroy() {
        record("ACTIVITY_DESTROY_BEGIN");
        try {
            // Receiver disconnect below owns the read-side shutdown. Calling
            // the explicit diagnostic socket hook here would race its own
            // scoped test operation and is not part of Activity cleanup.
            record("RACE_CONTROLLER_STATE phase=onDestroy idle="+R7C6TestBridge.raceControllerIdle());
            if(activeSocketRace) {
                record("SOCKET_CLOSE_BEGIN");
                try { R7C6TestBridge.shutdownActiveSocket(); }
                catch(Throwable t) { record("SOCKET_CLOSE_ERROR="+t.getClass().getName()); }
                record("SOCKET_CLOSE_END");
            }
            record("NATIVE_SHUTDOWN_BEGIN");
            if(secondaryHost!=null) { record("PRESENTATION_DISMISS_REQUESTED"); secondaryHost.close(); record("PRESENTATION_DISMISSED"); }
            long secondary=activeRaceSecondarySurface; activeRaceSecondarySurface=0;
            long primary=activeRacePrimarySurface; activeRacePrimarySurface=0;
            if(secondary>0) NativeBridge.nativeReleaseSurface(secondary);
            if(primary>0) NativeBridge.nativeReleaseSurface(primary);
            long receiver=activeRaceReceiver; activeRaceReceiver=0;
            if(receiver>0) { NativeBridge.nativeDisconnect(receiver); NativeBridge.nativeReleaseReceiver(receiver); }
            if(activityDestroyAudio!=null) { activityDestroyAudio.close(); activityDestroyAudio=null; }
            activityDestroyInput=null;
            requireNativeZero("Activity onDestroy cleanup");
            record("NATIVE_SHUTDOWN_END");
            record("ACTIVITY_DESTROY_PROJECT_OWNERS_RELEASED");
        } catch(Throwable t) { record("ACTIVITY_DESTROY_CLEANUP_ERROR="+t.getClass().getName()); }
        finally { super.onDestroy(); record("ACTIVITY_DESTROYED"); activityDestroyed.countDown(); }
    }
}
