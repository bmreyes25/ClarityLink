package org.claritylink.renderer;

import java.nio.ByteBuffer;

/** Lease value contract checks run on the API 17 UI thread; host lifecycle is exercised separately. */
public final class PaneLeaseTest {
    private static void require(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }

    public static void main(String[] args) {
        final PaneLease lease = new PaneLease(9L);
        final int[] calls = new int[] { 0 };
        lease.addRevocationCallback(new PaneLease.RevocationCallback() {
            public void onRevoked(PaneLease value) {
                require(value == lease, "callback receives its revoked lease");
                calls[0]++;
                throw new IllegalStateException("contained callback failure");
            }
        });
        require(lease.isValid(), "new lease starts valid");
        lease.revoke();
        lease.revoke();
        require(!lease.isValid() && calls[0] == 1, "revocation is permanent and callbacks run once");
        final int[] lateCalls = new int[] { 0 };
        lease.addRevocationCallback(new PaneLease.RevocationCallback() {
            public void onRevoked(PaneLease value) { lateCalls[0]++; }
        });
        require(!lease.isValid() && lateCalls[0] == 1, "late callback cannot revive a lease");

        boolean invalidGenerationRejected = false;
        try { new PaneLease(0L); }
        catch (IllegalArgumentException expected) { invalidGenerationRejected = true; }
        require(invalidGenerationRejected, "invalid generation fixture must be rejected");
        boolean malformedFrameRejected = false;
        try {
            new DecodedFrame(0, 2, 8, 1L, 0, 0, 0, 1, 2, ByteBuffer.allocate(16));
        } catch (IllegalArgumentException expected) { malformedFrameRejected = true; }
        require(malformedFrameRejected, "invalid frame fixture must be rejected by constructor bounds");
        System.out.println("PANE_LEASE_CONTRACT_PASS revoke=permanent callbacks=once invalid_generation=rejected malformed_frame=rejected");
    }
}
