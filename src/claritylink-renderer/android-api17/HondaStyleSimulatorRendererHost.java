package org.claritylink.renderer;

import android.view.View;
import android.widget.FrameLayout;

import org.claritylink.android.HondaStyleDisplayHostSimulator;

/** Bridges the renderer backend to the project-owned host simulator only. */
public final class HondaStyleSimulatorRendererHost implements Display1OutputBackend.Host {
    private final HondaStyleDisplayHostSimulator simulator;

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
        return simulator.ownsClarityContent(content, generation)
                && simulator.detachClarityContent(generation);
    }
}
