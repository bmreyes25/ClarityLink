package org.claritylink.android;

import android.app.Activity;
import android.content.Context;
import android.hardware.display.DisplayManager;
import android.hardware.usb.UsbManager;
import android.media.AudioFormat;
import android.os.Bundle;
import android.os.Debug;
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
import java.io.File;
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
    private SecondaryDisplayHost secondaryHost;
    private boolean started;
    private String runtimeFailure;

    public void onCreate(Bundle state) {
        super.onCreate(state);
        final FrameLayout root = new FrameLayout(this);
        PrimaryDisplayHost primary = new PrimaryDisplayHost(this);
        primary.setListener(new PrimaryDisplayHost.Listener() {
            public void onSurface(Surface surface) { synchronized(surfaceLock) { primarySurface=surface; } maybeStart(); }
            public void onSurfaceLost() { synchronized(surfaceLock) { primarySurface=null; } }
        });
        fallbackView = new SurfaceView(this);
        fallbackView.getHolder().addCallback(new SurfaceHolder.Callback() {
            public void surfaceCreated(SurfaceHolder holder) { synchronized(surfaceLock) { fallbackSecondarySurface=holder.getSurface(); } maybeStart(); }
            public void surfaceChanged(SurfaceHolder holder,int format,int width,int height) { }
            public void surfaceDestroyed(SurfaceHolder holder) { synchronized(surfaceLock) { fallbackSecondarySurface=null; } }
        });
        FrameLayout.LayoutParams p = new FrameLayout.LayoutParams(640,480,Gravity.TOP|Gravity.LEFT);
        root.addView(primary,p);
        FrameLayout.LayoutParams f = new FrameLayout.LayoutParams(240,180,Gravity.BOTTOM|Gravity.RIGHT);
        root.addView(fallbackView,f);
        setContentView(root);
        record("PROCESS_READY api="+android.os.Build.VERSION.SDK_INT+" runtime="+System.getProperty("java.vm.name"));
        enumerateDisplays();
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
                secondaryHost=new SecondaryDisplayHost(new SecondaryDisplayHost.Listener() {
                    public void state(DisplayPolicy.Admission state) { record("PRESENTATION_STATE="+state.name()); }
                    public void surface(Surface surface) { synchronized(surfaceLock) { presentationSurface=surface; } maybeStart(); }
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
            exerciseNativeSocketReceiver(primary,secondary,h110);
            exerciseJniExceptionSeams();
            recordMemory("baseline",0);
            for(int cycle=0;cycle<100;cycle++) {
                long generation=20000L+cycle;
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
                boolean wrongGeneration=NativeBridge.nativeTestIngestSyntheticPacket(receiver,generation,packet(generation+1,110,1100,h110));
                boolean wrongStream=NativeBridge.nativeTestIngestSyntheticPacket(receiver,generation,packet(generation,111,1100,h111));
                boolean frame110=NativeBridge.nativeTestIngestSyntheticPacket(receiver,generation,packet(generation,110,1100,h110));
                boolean frame111=NativeBridge.nativeTestIngestSyntheticPacket(receiver,generation,packet(generation,111,1101,h111));
                if(wrongGeneration || wrongStream || !frame110 || !frame111) allFrames=false;
                NativeBridge.nativeDisconnect(receiver);
                NativeBridge.nativeReleaseReceiver(receiver);
                NativeBridge.nativeReleaseSurface(p);
                NativeBridge.nativeReleaseSurface(s);
                boolean staleRejected=false;
                try { NativeBridge.nativeDisconnect(receiver); } catch(IllegalStateException expected) { staleRejected=true; }
                if(!staleRejected) throw new IllegalStateException("stale JNI handle accepted");
                long[] closed=NativeBridge.nativeDebugResourceCounts();
                for(int i=0;i<closed.length;i++) if(closed[i]!=0) throw new IllegalStateException("native owner leaked counter="+i+" cycle="+cycle);
                cycles++;
                if(cycles%10==0) recordMemory("cycle",cycles);
            }
            if(!allFrames) throw new IllegalStateException("generation/stream guard or H.264 Surface post failed");
            record("TYPE110_H264_ANDROID_SURFACE=PASS");
            record("TYPE111_H264_ANDROID_SURFACE=PASS");
            injectType111SurfaceLoss(primary,secondary);
            injectPrimarySurfaceLoss(primary,secondary);
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

    private void exerciseNativeSocketReceiver(Surface primary, Surface secondary, byte[] h264) throws Exception {
        final long generation=30200;
        final byte[] frame=packet(generation,110,1100,h264);
        final ServerSocket server=new ServerSocket(0,1,java.net.InetAddress.getByName("127.0.0.1"));
        server.setSoTimeout(3000);
        final Throwable[] peerFailure=new Throwable[1];
        Thread peer=new Thread(new Runnable() { public void run() {
            try {
                Socket accepted=server.accept(); accepted.setSoTimeout(3000);
                OutputStream out=accepted.getOutputStream();
                // Deliberately fragment the frame to exercise adapter partial reads.
                for(int i=0;i<frame.length;i+=37) { int n=Math.min(37,frame.length-i); out.write(frame,i,n); out.flush(); }
                accepted.shutdownOutput(); accepted.close();
            } catch(Throwable t) { peerFailure[0]=t; }
        }},"r7c3-native-socket-peer");
        long p=NativeBridge.nativeAttachSurface(primary,generation,110,8101);
        long s=NativeBridge.nativeAttachSurface(secondary,generation,111,8102);
        long receiver=NativeBridge.nativeCreateReceiver(generation,p,s,true);
        if(!NativeBridge.nativeSetup(receiver,generation,1100,1101,true)) throw new IllegalStateException("socket receiver SETUP failed");
        int fdBefore=new File("/proc/self/fd").list().length;
        peer.start();
        boolean accepted=R7C3TestBridge.receiveSocketFrame(receiver,generation,"127.0.0.1",server.getLocalPort(),3000);
        peer.join(4000); server.close();
        if(!accepted || peer.isAlive() || peerFailure[0]!=null) throw new IllegalStateException("native socket LAB frame did not reach ReceiverGeneration");
        NativeBridge.nativeDisconnect(receiver); NativeBridge.nativeReleaseReceiver(receiver);
        NativeBridge.nativeReleaseSurface(p); NativeBridge.nativeReleaseSurface(s);
        requireNativeZero("native socket receiver cleanup");
        int fdAfter=new File("/proc/self/fd").list().length;
        if(fdAfter>fdBefore+1) throw new IllegalStateException("native socket retained descriptors before="+fdBefore+" after="+fdAfter);
        record("NATIVE_POSIX_SOCKET_JNI_RECEIVER=PASS protocol=LAB_LOOPBACK fdBefore="+fdBefore+" fdAfter="+fdAfter);
    }

    private void exerciseJniExceptionSeams() {
        boolean pending=false;
        try { R7C3TestBridge.pendingExceptionProbe(); }
        catch(IllegalArgumentException expected) { pending=expected.getMessage().contains("R7C3 pending-exception probe"); }
        if(!pending) throw new IllegalStateException("JNI-created pending exception was not preserved");
        boolean lookup=false;
        try { R7C3TestBridge.lookupFailureProbe(); }
        catch(ClassNotFoundException expected) { lookup=true; }
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
    private void record(String line) { Log.i(TAG,line); }
    private void saveResult(int cycles,String error) {
        String result=(error==null?"RESULT=PASS":"RESULT=FAIL")+"\nCYCLES="+cycles+"\nERROR="+(error==null?"NONE":error)+"\nRUNTIME="+System.getProperty("java.vm.name")+"\nAPI="+android.os.Build.VERSION.SDK_INT+"\n";
        try { FileOutputStream out=openFileOutput("r7c2-result.txt",MODE_PRIVATE); out.write(result.getBytes("UTF-8")); out.close(); }
        catch(Exception e) { Log.e(TAG,"result write failed",e); }
        Log.i(TAG,result);
    }
    protected void onPause() { super.onPause(); record("HOST_PAUSED"); }
    protected void onResume() { super.onResume(); record("HOST_RESUMED"); }
}
