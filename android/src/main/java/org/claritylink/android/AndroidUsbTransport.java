package org.claritylink.android;

import android.app.PendingIntent;
import android.content.Context;
import android.hardware.usb.UsbDevice;
import android.hardware.usb.UsbDeviceConnection;
import android.hardware.usb.UsbEndpoint;
import android.hardware.usb.UsbInterface;
import android.hardware.usb.UsbManager;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.ArrayList;
import java.util.List;

/** Generic API12+ USB host boundary. No descriptor matching or accessory impersonation. */
public final class AndroidUsbTransport {
    public interface PermissionResult { void complete(boolean granted); }
    public interface DeviceVisitor { void found(UsbDevice device); }
    public static final int MAX_TRANSFER = 64 * 1024;
    private final UsbManager manager;
    private UsbDeviceConnection connection;
    private long generation;
    private final List<UsbInterface> claimed=new ArrayList<UsbInterface>();
    public AndroidUsbTransport(Context context) {
        manager=(UsbManager)context.getSystemService(Context.USB_SERVICE);
        if(manager==null) throw new IllegalStateException("UsbManager unavailable");
    }
    public Map<String,UsbDevice> discover() { return Collections.unmodifiableMap(new HashMap<String,UsbDevice>(manager.getDeviceList())); }
    public boolean hasPermission(UsbDevice device) { return device != null && manager.hasPermission(device); }
    public void requestPermission(UsbDevice device, PendingIntent resultIntent) {
        if(device==null || resultIntent==null) throw new IllegalArgumentException("device and result intent required");
        manager.requestPermission(device,resultIntent);
    }
    public synchronized boolean open(UsbDevice device,long generation) {
        close(); if(device==null || generation<=0 || !manager.hasPermission(device)) return false;
        UsbDeviceConnection candidate=manager.openDevice(device); if(candidate==null) return false;
        this.connection=candidate; this.generation=generation; return true;
    }
    public synchronized int control(int requestType,int request,int value,int index,byte[] buffer,int length,int timeout,long gen) {
        if(connection==null || gen!=generation || buffer==null || length<0 || length>MAX_TRANSFER || length>buffer.length || timeout<1) return -1;
        return connection.controlTransfer(requestType,request,value,index,buffer,length,timeout);
    }
    public synchronized boolean claimInterface(UsbInterface usbInterface,boolean force,long gen) {
        if(connection==null || usbInterface==null || gen!=generation || !connection.claimInterface(usbInterface,force)) return false;
        claimed.add(usbInterface); return true;
    }
    public synchronized int bulk(UsbEndpoint endpoint,byte[] buffer,int length,int timeout,long gen) {
        if(connection==null || endpoint==null || gen!=generation || buffer==null || length<0 ||
           length>MAX_TRANSFER || length>buffer.length || timeout<1) return -1;
        return connection.bulkTransfer(endpoint,buffer,length,timeout);
    }
    public synchronized void invalidate(long gen) { if(gen==generation) close(); }
    public synchronized void close() {
        if(connection!=null) {
            for(int i=claimed.size()-1;i>=0;i--) connection.releaseInterface(claimed.get(i));
            claimed.clear(); connection.close(); connection=null;
        }
        generation=0;
    }
}
