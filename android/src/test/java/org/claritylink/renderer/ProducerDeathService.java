package org.claritylink.renderer;

import android.app.Service;
import android.content.Intent;
import android.os.Binder;
import android.os.IBinder;
import android.os.Parcel;
import android.os.Process;
import android.os.RemoteException;

/**
 * Synthetic producer for the CL-INT-04 instrumentation test. Declared with android:process=":producer"
 * so it is a separate OS process whose Binder the host links to. It sends nothing and holds no
 * ClarityLink state; it can only report its pid and kill itself on request.
 */
public final class ProducerDeathService extends Service {
    public static final int TX_PID = IBinder.FIRST_CALL_TRANSACTION;
    public static final int TX_DIE = IBinder.FIRST_CALL_TRANSACTION + 1;

    private final Binder binder = new Binder() {
        @Override
        protected boolean onTransact(int code, Parcel data, Parcel reply, int flags) throws RemoteException {
            if (code == TX_PID) {
                reply.writeInt(Process.myPid());
                return true;
            }
            if (code == TX_DIE) {
                Process.killProcess(Process.myPid());  // unexpected termination: no callbacks run
                return true;
            }
            return super.onTransact(code, data, reply, flags);
        }
    };

    @Override
    public IBinder onBind(Intent intent) { return binder; }
}
