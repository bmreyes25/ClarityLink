package org.claritylink.android;

import android.app.Activity;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.widget.FrameLayout;

import org.claritylink.renderer.Display1OutputBackend;
import org.claritylink.renderer.NavigationGenerationLedger;
import org.claritylink.renderer.HondaStyleSimulatorRendererHost;
import org.claritylink.renderer.NavigationUpdate;
import org.claritylink.renderer.SimulatedExternalDisplayCompositor;
import org.claritylink.renderer.StructuredNavigationOutputBackend;

/** Emulator-only synthetic acceptance scenario; never connects to vehicle services. */
public final class StructuredNavigationLabActivity extends Activity {
    private static final String TAG = "ClarityLinkNavLab";

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        try {
            runScenario();
        } catch (Throwable failure) {
            Log.e(TAG, "CL_FACTORY_03_API17_RUNTIME_FAIL", failure);
            finish();
            return;
        }
        Log.i(TAG, "CL_FACTORY_03_API17_RUNTIME_PASS updates=2 stale_rejected=true "
                + "interrupt_withdrawal=true host_recreated=true fresh_generation=true "
                + "cleanup=true type111_isolated=true");
        finish();
    }

    private void runScenario() {
        FrameLayout root = new FrameLayout(this);
        HondaStyleDisplayHostSimulator firstHost = new HondaStyleDisplayHostSimulator(this);
        root.addView(firstHost.getDisplayRoot(), new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));
        setContentView(root);
        HondaStyleSimulatorRendererHost firstRendererHost = new HondaStyleSimulatorRendererHost(firstHost);
        NavigationGenerationLedger ledger = new NavigationGenerationLedger();
        StructuredNavigationOutputBackend backend = new StructuredNavigationOutputBackend(
                firstRendererHost, new Display1OutputBackend.Viewport(0, 0, 800, 480), ledger);
        backend.beginSession(71, 100);
        require(backend.submit(update(71, 100, 1, "left", 500, "m", "Test Avenue")), "initial update");
        require(backend.submit(update(71, 100, 2, "straight", 350, "m", "Test Avenue")), "replacement update");
        require(backend.contentView().latestUpdate().sequence == 2, "replacement visible in model");
        require(drawContainsWhiteNavigationText(backend.contentView()), "navigation text rendered to API17 Canvas");
        require(!backend.submit(update(71, 100, 2, "right", 20, "m", "Duplicate")), "duplicate sequence");
        require(!backend.submit(update(71, 99, 3, "right", 20, "m", "Stale")), "stale generation");

        SimulatedExternalDisplayCompositor type111 = new SimulatedExternalDisplayCompositor();
        require(type111.begin(1), "Type111 fixture generation");
        require(type111.accept(1, 1, 1, 1, 4, 4), "Type111 fixture frame");
        long type111Frames = type111.acceptedFrames();
        int type111Bytes = type111.latestPayloadBytes();

        firstHost.setSimulatedStockWarningVisible(true);
        require(backend.contentView().latestUpdate() == null, "warning synchronously withdraws navigation");
        require(!backend.submit(update(71, 100, 3, "right", 20, "m", "Blocked")), "warning blocks old owner");
        firstHost.setSimulatedStockWarningVisible(false);
        require(backend.contentView().latestUpdate() == null, "clearing warning does not restore old guidance");
        backend.beginSession(71, 101);
        require(!backend.submit(update(71, 100, 4, "right", 20, "m", "Stale")), "old generation after warning");
        require(backend.submit(update(71, 101, 1, "right", 200, "m", "Fresh Route")), "fresh generation update");
        backend.withdraw();
        require(backend.contentView().latestUpdate() == null, "explicit withdrawal clears content");
        require(!backend.submit(update(71, 101, 2, "right", 100, "m", "Withdrawn")),
                "withdrawn generation cannot restore guidance");
        backend.beginSession(71, 102);
        require(backend.submit(update(71, 102, 1, "straight", 90, "m", "Fresh Route")),
                "new generation required after withdrawal");
        require(type111.acceptedFrames() == type111Frames && type111.latestPayloadBytes() == type111Bytes,
                "navigation leaves video ownership unchanged");

        backend.close();
        firstHost.close();
        HondaStyleDisplayHostSimulator secondHost = new HondaStyleDisplayHostSimulator(this);
        setContentView(secondHost.getDisplayRoot());
        StructuredNavigationOutputBackend recovered = new StructuredNavigationOutputBackend(
                new HondaStyleSimulatorRendererHost(secondHost),
                new Display1OutputBackend.Viewport(0, 0, 800, 480), ledger);
        boolean reusedGenerationRejected = false;
        try { recovered.beginSession(71, 102); }
        catch (IllegalArgumentException expected) { reusedGenerationRejected = true; }
        require(reusedGenerationRejected, "recreated host cannot reuse the previous generation");
        recovered.beginSession(71, 103);
        require(!recovered.submit(update(71, 102, 2, "left", 50, "m", "Old Host")), "old host generation rejected");
        require(recovered.submit(update(71, 103, 1, "arrive", 0, "m", "Destination")), "reconnected host update");
        View rendered = recovered.contentView();
        recovered.close();
        require(rendered.getParent() == null && rendered.getVisibility() == View.GONE,
                "cleanup detaches and hides synthetic content");
        secondHost.close();
        type111.end(1);
    }

    private static NavigationUpdate update(long session, long generation, long sequence,
            String maneuver, double distance, String unit, String road) {
        return new NavigationUpdate(session, generation, sequence, maneuver, distance, unit, road);
    }

    private static boolean drawContainsWhiteNavigationText(View view) {
        int width = 800;
        int height = 480;
        view.measure(View.MeasureSpec.makeMeasureSpec(width, View.MeasureSpec.EXACTLY),
                View.MeasureSpec.makeMeasureSpec(height, View.MeasureSpec.EXACTLY));
        view.layout(0, 0, width, height);
        Bitmap bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
        view.draw(new Canvas(bitmap));
        int whitePixels = 0;
        for (int y = 0; y < height && whitePixels == 0; y++)
            for (int x = 0; x < width; x++)
                if ((bitmap.getPixel(x, y) & 0x00ffffff) == 0x00ffffff) whitePixels++;
        bitmap.recycle();
        return whitePixels > 0;
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
