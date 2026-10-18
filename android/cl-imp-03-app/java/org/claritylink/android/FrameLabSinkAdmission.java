package org.claritylink.android;

import android.os.IBinder;
import android.os.Parcel;
import android.os.Parcelable;

/** One-use compositor-issued admission passed only to the private Type110 lab service. */
final class FrameLabSinkAdmission implements Parcelable {
    final long sessionId;
    final IBinder grant;

    FrameLabSinkAdmission(long sessionId, IBinder grant) {
        if (sessionId <= 0L || grant == null) throw new IllegalArgumentException("admission required");
        this.sessionId = sessionId;
        this.grant = grant;
    }

    private FrameLabSinkAdmission(Parcel source) {
        sessionId = source.readLong();
        grant = source.readStrongBinder();
    }

    public int describeContents() { return 0; }
    public void writeToParcel(Parcel destination, int flags) {
        destination.writeLong(sessionId);
        destination.writeStrongBinder(grant);
    }

    public static final Creator<FrameLabSinkAdmission> CREATOR =
            new Creator<FrameLabSinkAdmission>() {
                public FrameLabSinkAdmission createFromParcel(Parcel source) {
                    return new FrameLabSinkAdmission(source);
                }
                public FrameLabSinkAdmission[] newArray(int size) {
                    return new FrameLabSinkAdmission[size];
                }
            };
}
