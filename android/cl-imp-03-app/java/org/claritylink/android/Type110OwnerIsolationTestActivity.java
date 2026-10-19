package org.claritylink.android;

import android.app.Activity;
import android.os.Bundle;
import android.util.Log;

import java.io.File;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/** Lab-only runtime regression: concurrent session handoffs remain separately consumable. */
public final class Type110OwnerIsolationTestActivity extends Activity {
    private static final String TAG = "ClarityLinkCLIMP03";

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        new Thread(new Runnable() {
            @Override public void run() { runIsolationCheck(); }
        }, "cl-owner-isolation-test").start();
    }

    private void runIsolationCheck() {
        ClarityLinkDisplayApplication app = (ClarityLinkDisplayApplication) getApplication();
        if (!verifyExpiredOwnerRecovery(app)) return;
        long sessionA = app.nextGeneration();
        long sessionB = app.nextGeneration();
        FrameStreamIdentity ownerA = new FrameStreamIdentity(sessionA,
                FrameStreamIdentity.TYPE110, 11001L, sessionA, FrameStreamIdentity.OUTPUT_PRIMARY_LAB);
        FrameStreamIdentity deathA = new FrameStreamIdentity(sessionA,
                FrameStreamIdentity.TYPE111, 11101L, sessionA + 1L, FrameStreamIdentity.OUTPUT_SECONDARY_VIEW);
        FrameStreamIdentity ownerB = new FrameStreamIdentity(sessionB,
                FrameStreamIdentity.TYPE110, 11002L, sessionB, FrameStreamIdentity.OUTPUT_PRIMARY_LAB);
        FrameStreamIdentity deathB = new FrameStreamIdentity(sessionB,
                FrameStreamIdentity.TYPE111, 11102L, sessionB + 1L, FrameStreamIdentity.OUTPUT_SECONDARY_VIEW);
        final boolean[] issued = new boolean[2];
        final Throwable[] failures = new Throwable[2];
        final CountDownLatch ready = new CountDownLatch(2);
        final CountDownLatch start = new CountDownLatch(1);
        Thread a = issueThread(0, ownerA, deathA, 101L, 1101, ready, start, issued, failures);
        Thread b = issueThread(1, ownerB, deathB, 202L, 2202, ready, start, issued, failures);
        a.start();
        b.start();
        try {
            if (!ready.await(2L, TimeUnit.SECONDS)) throw new IllegalStateException("issue_threads_not_ready");
            start.countDown();
            a.join(3000L);
            b.join(3000L);
            if (a.isAlive() || b.isAlive() || failures[0] != null || failures[1] != null ||
                    !issued[0] || !issued[1])
                throw new IllegalStateException("concurrent_issue_failed issued_a=" + issued[0] +
                        " issued_b=" + issued[1] + " a_alive=" + a.isAlive() +
                        " b_alive=" + b.isAlive() + " failure_a=" + failureName(failures[0]) +
                        " failure_b=" + failureName(failures[1]));
            if (!Type110LabProbeOwnership.hasPending(this, deathA) ||
                    !Type110LabProbeOwnership.hasPending(this, deathB))
                throw new IllegalStateException("session_record_overwritten");
            Type110LabProbeOwnership.Record consumedB = Type110LabProbeOwnership.consume(this, deathB);
            Type110LabProbeOwnership.Record consumedA = Type110LabProbeOwnership.consume(this, deathA);
            if (consumedA == null || consumedB == null ||
                    !ownerA.equals(consumedA.identity) || !ownerB.equals(consumedB.identity) ||
                    consumedA.lastFrameId != 101L || consumedB.lastFrameId != 202L ||
                    consumedA.sinkPid != 1101 || consumedB.sinkPid != 2202 ||
                    Type110LabProbeOwnership.hasPending(this, deathA) ||
                    Type110LabProbeOwnership.hasPending(this, deathB))
                throw new IllegalStateException("session_record_cross_routed_or_not_consumed");
            Log.i(TAG, "TYPE110_OWNER_SESSION_ISOLATION_PASS session_a=" + sessionA +
                    " session_b=" + sessionB + " sessions_distinct=true concurrent_issue=true " +
                    "reverse_consume=true records_remaining=0");
        } catch (Throwable failure) {
            Log.e(TAG, "TYPE110_OWNER_SESSION_ISOLATION_FAIL reason=" + failure.getMessage(), failure);
        } finally {
            start.countDown();
            try { a.join(3000L); } catch (InterruptedException ignored) { Thread.currentThread().interrupt(); }
            try { b.join(3000L); } catch (InterruptedException ignored) { Thread.currentThread().interrupt(); }
            Type110LabProbeOwnership.consume(this, deathA);
            Type110LabProbeOwnership.consume(this, deathB);
            runOnUiThread(new Runnable() {
                @Override public void run() { finish(); }
            });
        }
    }

    private boolean verifyExpiredOwnerRecovery(ClarityLinkDisplayApplication app) {
        FrameStreamIdentity[] deaths = new FrameStreamIdentity[32];
        File directory = getFilesDir();
        try {
            for (int index = 0; index < deaths.length; index++) {
                long session = app.nextGeneration();
                FrameStreamIdentity owner = new FrameStreamIdentity(session,
                        FrameStreamIdentity.TYPE110, 12000L + index, session,
                        FrameStreamIdentity.OUTPUT_PRIMARY_LAB);
                deaths[index] = new FrameStreamIdentity(session,
                        FrameStreamIdentity.TYPE111, 13000L + index, session + 1L,
                        FrameStreamIdentity.OUTPUT_SECONDARY_VIEW);
                if (!Type110LabProbeOwnership.issue(this, owner, deaths[index], index, 3000 + index))
                    throw new IllegalStateException("fill_pending_owner_cap_failed_at=" + index);
            }
            long rejectedSession = app.nextGeneration();
            FrameStreamIdentity rejectedOwner = new FrameStreamIdentity(rejectedSession,
                    FrameStreamIdentity.TYPE110, 14001L, rejectedSession,
                    FrameStreamIdentity.OUTPUT_PRIMARY_LAB);
            FrameStreamIdentity rejectedDeath = new FrameStreamIdentity(rejectedSession,
                    FrameStreamIdentity.TYPE111, 14002L, rejectedSession + 1L,
                    FrameStreamIdentity.OUTPUT_SECONDARY_VIEW);
            if (Type110LabProbeOwnership.issue(this, rejectedOwner, rejectedDeath, 1L, 4001))
                throw new IllegalStateException("owner_cap_not_enforced");
            File[] files = directory.listFiles();
            if (files == null) throw new IllegalStateException("private_files_unavailable");
            int staleRecords = 0;
            for (File file : files) {
                if (file.getName().startsWith("cl_r4_type110_probe_owner_") &&
                        file.getName().endsWith(".record")) {
                    if (!file.setLastModified(1L)) throw new IllegalStateException("age_record_failed");
                    staleRecords++;
                }
            }
            if (staleRecords != deaths.length) throw new IllegalStateException("unexpected_pending_record_count");
            File staleTemp = new File(directory, "cl_r4_type110_probe_owner_deadbeef.tmp");
            File staleClaim = new File(directory, "cl_r4_type110_probe_owner_deadbee0.claimed");
            if (!staleTemp.createNewFile() || !staleClaim.createNewFile())
                throw new IllegalStateException("orphan_artifact_seed_failed");
            long recoveredSession = app.nextGeneration();
            FrameStreamIdentity recoveredOwner = new FrameStreamIdentity(recoveredSession,
                    FrameStreamIdentity.TYPE110, 15001L, recoveredSession,
                    FrameStreamIdentity.OUTPUT_PRIMARY_LAB);
            FrameStreamIdentity recoveredDeath = new FrameStreamIdentity(recoveredSession,
                    FrameStreamIdentity.TYPE111, 15002L, recoveredSession + 1L,
                    FrameStreamIdentity.OUTPUT_SECONDARY_VIEW);
            if (!Type110LabProbeOwnership.issue(this, recoveredOwner, recoveredDeath, 2L, 5001) ||
                    !Type110LabProbeOwnership.hasPending(this, recoveredDeath) ||
                    Type110LabProbeOwnership.consume(this, recoveredDeath) == null)
                throw new IllegalStateException("owner_cap_recovery_failed");
            for (File file : directory.listFiles()) {
                String name = file.getName();
                if (name.startsWith("cl_r4_type110_probe_owner_") &&
                        (name.endsWith(".record") || name.endsWith(".tmp") || name.endsWith(".claimed")))
                    throw new IllegalStateException("abandoned_owner_artifact_remains=" + name);
            }
            Log.i(TAG, "TYPE110_OWNER_CAP_RECOVERY_PASS pending_cap=32 cap_rejected=true " +
                    "expired_records_pruned=32 orphan_temp_pruned=true orphan_claim_pruned=true " +
                    "new_session_issued=true artifacts_remaining=0");
            return true;
        } catch (Throwable failure) {
            Log.e(TAG, "TYPE110_OWNER_CAP_RECOVERY_FAIL reason=" + failure.getMessage(), failure);
            return false;
        }
    }

    private Thread issueThread(final int index, final FrameStreamIdentity owner,
            final FrameStreamIdentity death, final long frameId, final int sinkPid,
            final CountDownLatch ready, final CountDownLatch start,
            final boolean[] issued, final Throwable[] failures) {
        return new Thread(new Runnable() {
            @Override public void run() {
                ready.countDown();
                try {
                    if (!start.await(2L, TimeUnit.SECONDS)) throw new IllegalStateException("issue_start_timeout");
                    issued[index] = Type110LabProbeOwnership.issue(
                            Type110OwnerIsolationTestActivity.this, owner, death, frameId, sinkPid);
                } catch (Throwable failure) {
                    failures[index] = failure;
                }
            }
        }, "cl-owner-issue-" + index);
    }

    private static String failureName(Throwable failure) {
        return failure == null ? "none" : failure.getClass().getSimpleName() + ":" +
                String.valueOf(failure.getMessage());
    }
}
