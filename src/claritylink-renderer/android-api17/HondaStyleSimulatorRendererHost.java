package org.claritylink.renderer;

import android.view.View;
import android.widget.FrameLayout;
import java.util.ArrayList;
import java.util.List;

import org.claritylink.android.HondaStyleDisplayHostSimulator;

/** Bridges the renderer backend to the project-owned host simulator only. */
public final class HondaStyleSimulatorRendererHost implements Display1OutputBackend.EventHost {
    private final HondaStyleDisplayHostSimulator simulator;
    private final List<Display1OutputBackend.PaneEventListener> listeners =
            new ArrayList<Display1OutputBackend.PaneEventListener>();
    private long eventSequence;
    private int detachCalls;
    private volatile boolean hostValid = true;
    private volatile RendererViewport paneViewport = RendererViewport.fullCanvasTestOnly();

    public HondaStyleSimulatorRendererHost(HondaStyleDisplayHostSimulator simulator) {
        if (simulator == null) throw new IllegalArgumentException("simulator required");
        this.simulator = simulator;
    }

    public FrameLayout getMainLayer() { return simulator.getCustomContentContainer(); }
    public boolean isNavigationPageActive() { return simulator.isNavigationActive(); }

    public boolean attachContent(View content, long generation) {
        return simulator.attachClarityContent(content, generation);
    }

    public boolean detachContent(View content, long generation) {
        detachCalls++;
        return simulator.ownsClarityContent(content, generation)
                && simulator.detachClarityContent(generation);
    }

    public synchronized void addPaneEventListener(Display1OutputBackend.PaneEventListener listener) {
        if (listener == null) throw new IllegalArgumentException("listener required");
        if (!listeners.contains(listener)) listeners.add(listener);
    }

    public synchronized void removePaneEventListener(Display1OutputBackend.PaneEventListener listener) {
        listeners.remove(listener);
    }

    public boolean isHostValid() { return hostValid && !simulator.isClosed(); }
    public boolean isInterruptActive() { return simulator.isWarningVisible(); }
    public RendererViewport getPaneViewport() { return paneViewport; }
    public Object generationOwner() { return simulator; }
    public synchronized int listenerCountForTest() { return listeners.size(); }
    public synchronized long eventSequenceForTest() { return eventSequence; }
    public int detachCallsForTest() { return detachCalls; }

    /** Test adapter entry point: model state changes only in the project-owned simulator. */
    public void simulatePageSelected() {
        simulator.setNavigationActive(true);
        publish(PaneEvent.Type.PAGE_SELECTED, false, null);
    }
    public void simulatePageDeselected() {
        simulator.setNavigationActive(false);
        publish(PaneEvent.Type.PAGE_DESELECTED, false, null);
    }
    public void simulateInterruptOn() {
        simulator.setSimulatedStockWarningVisible(true);
        publish(PaneEvent.Type.INTERRUPT_ON, false, null);
    }
    public void simulateInterruptOff() {
        simulator.setSimulatedStockWarningVisible(false);
        publish(PaneEvent.Type.INTERRUPT_OFF, false, null);
    }
    public void simulateHostLost() {
        hostValid = false;
        publish(PaneEvent.Type.HOST_LOST, false, null);
    }
    public void simulateHostRestored(boolean valid) {
        hostValid = valid;
        publish(PaneEvent.Type.HOST_RESTORED, valid, null);
    }
    public void simulateViewportChanged(RendererViewport viewport) {
        if (viewport == null) throw new IllegalArgumentException("synthetic viewport required");
        paneViewport = viewport;
        publish(PaneEvent.Type.VIEWPORT_CHANGED, false, viewport);
    }

    /** Allows deterministic delayed/stale callback tests without changing simulator code. */
    public void dispatchTestEvent(PaneEvent event) {
        if (event == null) throw new IllegalArgumentException("event required");
        deliver(event);
    }

    private void publish(PaneEvent.Type type, boolean valid, RendererViewport viewport) {
        final PaneEvent event;
        synchronized (this) {
            eventSequence++;
            event = type == PaneEvent.Type.HOST_RESTORED
                    ? new PaneEvent(type, eventSequence, valid)
                    : (type == PaneEvent.Type.VIEWPORT_CHANGED
                        ? new PaneEvent(type, eventSequence, viewport)
                        : new PaneEvent(type, eventSequence));
        }
        deliver(event);
    }

    private void deliver(PaneEvent event) {
        List<Display1OutputBackend.PaneEventListener> copy;
        synchronized (this) {
            if (event.sequence > eventSequence) eventSequence = event.sequence;
            copy = new ArrayList<Display1OutputBackend.PaneEventListener>(listeners);
        }
        for (int i = 0; i < copy.size(); i++) {
            try { copy.get(i).onPaneEvent(event); } catch (RuntimeException ignored) { }
        }
    }
}
