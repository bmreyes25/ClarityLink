package org.claritylink.renderer;

/** Immutable lifecycle notification from a simulated pane host. */
public final class PaneEvent {
    public enum Type {
        PAGE_SELECTED, PAGE_DESELECTED, INTERRUPT_ON, INTERRUPT_OFF,
        HOST_LOST, HOST_RESTORED, VIEWPORT_CHANGED
    }

    public final Type type;
    public final long sequence;
    public final boolean valid;
    public final RendererViewport viewport;

    public PaneEvent(Type type, long sequence) { this(type, sequence, false, null); }
    public PaneEvent(Type type, long sequence, boolean valid) { this(type, sequence, valid, null); }
    public PaneEvent(Type type, long sequence, RendererViewport viewport) {
        this(type, sequence, false, viewport);
    }
    private PaneEvent(Type type, long sequence, boolean valid, RendererViewport viewport) {
        if (type == null || sequence <= 0) throw new IllegalArgumentException("valid pane event required");
        this.type = type;
        this.sequence = sequence;
        this.valid = valid;
        this.viewport = viewport;
    }
}
