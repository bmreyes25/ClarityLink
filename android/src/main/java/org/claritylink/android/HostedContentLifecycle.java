package org.claritylink.android;

/** Lifecycle callbacks for project-owned content attached to the host simulator. */
public interface HostedContentLifecycle {
    int WARNING_PREEMPTION = 1;
    int NAVIGATION_EXIT = 2;
    int HOST_CLOSED = 3;
    int CONTENT_DETACHED = 4;

    void onHostSuspended(int reason, long generation);
    void onHostResumed(long generation);
}
