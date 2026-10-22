package org.claritylink.renderer;

/** Semantic main-content contract; deliberately has no DecodedFrame overload. */
public interface StructuredNavigationSink {
    void beginSession(long sessionId, long generation);
    boolean submit(NavigationUpdate update);
    void withdraw();
    void close();
}
