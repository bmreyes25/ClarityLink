package org.claritylink.android;

import android.content.Context;
import android.graphics.Point;
import android.hardware.display.DisplayManager;
import android.view.Display;
import android.view.WindowManager;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** API17 inventory. Display type remains UNKNOWN because API17 exposes no stable public type API. */
public final class DisplayDiscovery {
    public static final class Info {
        public final int id, width, height, rotation;
        public final float refreshHz;
        public final String name, type;
        public final boolean valid;
        Info(Display d) {
            id = d.getDisplayId(); name = d.getName(); type = "UNKNOWN";
            Point p = new Point(); d.getRealSize(p); width = p.x; height = p.y;
            rotation = d.getRotation(); refreshHz = d.getRefreshRate(); valid = d.isValid();
        }
    }
    public interface Selector { boolean matches(Info info); }
    private final DisplayManager manager;
    public DisplayDiscovery(Context context) {
        manager = (DisplayManager) context.getSystemService(Context.DISPLAY_SERVICE);
        if (manager == null) throw new IllegalStateException("DisplayManager unavailable");
    }
    public List<Info> enumerate() {
        Display[] displays = manager.getDisplays();
        List<Info> out = new ArrayList<Info>();
        if (displays != null) for (Display d : displays) if (d != null) out.add(new Info(d));
        return Collections.unmodifiableList(out);
    }
    public Display select(Selector selector) {
        if (selector == null) return null;
        Display selected = null;
        for (Display d : manager.getDisplays()) {
            if (d == null || !d.isValid() || !selector.matches(new Info(d))) continue;
            if (selected != null) return null; // Ambiguous identity fails closed.
            selected = d;
        }
        return selected;
    }
}
