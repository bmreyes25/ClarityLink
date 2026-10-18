package org.claritylink.android;

import android.content.Context;
import android.content.Intent;
import android.os.SystemClock;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.RandomAccessFile;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.channels.OverlappingFileLockException;

/** One-use, app-private handoff for the lab-owned Type110 stream after test-process death. */
final class Type110LabProbeOwnership {
    private static final int MAGIC = 0x434c5031;
    private static final int VERSION = 2;
    private static final String RECORD_PREFIX = "cl_r4_type110_probe_owner_";
    private static final String LOCK = "cl_r4_type110_probe_owner.lock";
    private static final String RECORD_SUFFIX = ".record";
    private static final int MAX_PENDING_OWNERS = 32;
    private static final long OWNER_RECORD_TTL_MS = 5L * 60L * 1000L;
    private static final long LOCK_WAIT_MS = 1000L;
    private static final String EXTRA_DEATH_SESSION = "expected_death_session";
    private static final String EXTRA_DEATH_TYPE = "expected_death_type";
    private static final String EXTRA_DEATH_CONNECTION = "expected_death_connection";
    private static final String EXTRA_DEATH_GENERATION = "expected_death_generation";
    private static final String EXTRA_DEATH_OUTPUT = "expected_death_output";
    private static final long TEARDOWN_GRANT_TTL_MS = 60000L;
    private static final String TEARDOWN_SUFFIX = ".teardown";

    static final class Record {
        final FrameStreamIdentity identity;
        final FrameStreamIdentity expectedType111Death;
        final long lastFrameId;
        final int sinkPid;

        Record(FrameStreamIdentity identity, FrameStreamIdentity expectedType111Death,
                long lastFrameId, int sinkPid) {
            this.identity = identity;
            this.expectedType111Death = expectedType111Death;
            this.lastFrameId = lastFrameId;
            this.sinkPid = sinkPid;
        }
    }

    private Type110LabProbeOwnership() { }

    private static final class OwnershipLock {
        final RandomAccessFile file;
        final FileLock lock;

        OwnershipLock(RandomAccessFile file, FileLock lock) {
            this.file = file;
            this.lock = lock;
        }

        void close() {
            try { lock.release(); } catch (Exception ignored) { }
            try { file.close(); } catch (Exception ignored) { }
        }
    }

    /** Cross-process lock; the OS releases it if a probe process dies mid-claim. */
    private static OwnershipLock acquire(Context context) {
        if (context == null) return null;
        RandomAccessFile file = null;
        try {
            file = new RandomAccessFile(new File(context.getFilesDir(), LOCK), "rw");
            FileChannel channel = file.getChannel();
            long deadline = SystemClock.elapsedRealtime() + LOCK_WAIT_MS;
            do {
                try {
                    FileLock lock = channel.tryLock();
                    if (lock != null) return new OwnershipLock(file, lock);
                } catch (OverlappingFileLockException alreadyLockedInProcess) {
                    // Another class caller in this VM owns the claim transaction.
                }
                SystemClock.sleep(10L);
            } while (SystemClock.elapsedRealtime() < deadline);
        } catch (Exception unavailable) {
            // Fail closed if internal storage or cross-process locking is unavailable.
        }
        if (file != null) try { file.close(); } catch (Exception ignored) { }
        return null;
    }

    /** Per-session files prevent one live session from replacing another session's handoff. */
    private static File sessionFile(File directory, long sessionId, String suffix) {
        return new File(directory, RECORD_PREFIX + Long.toHexString(sessionId) + suffix);
    }

    /** Count live records while holding the shared lock so concurrent sessions obey the same cap. */
    private static int pendingOwnerCount(File directory) {
        File[] files = directory.listFiles();
        if (files == null) return -1;
        int count = 0;
        for (File file : files) {
            String name = file.getName();
            if (name.startsWith(RECORD_PREFIX) && name.endsWith(RECORD_SUFFIX)) count++;
        }
        return count;
    }

    /**
     * Remove crash leftovers under the global lock. A .tmp or .claimed artifact cannot belong
     * to a live operation because every operation holds this same lock until it finishes.
     * Unconsumed records are useful only for the immediate Binder-death handoff; expiring them
     * bounds abandoned sessions while preserving the short recovery window.
     */
    private static boolean pruneAbandonedArtifacts(Context context, File directory) {
        File[] files = directory.listFiles();
        if (files == null) return false;
        long now = System.currentTimeMillis();
        for (File file : files) {
            String name = file.getName();
            if (!name.startsWith(RECORD_PREFIX)) continue;
            boolean temporary = name.endsWith(".tmp");
            boolean claimed = name.endsWith(".claimed");
            boolean record = name.endsWith(RECORD_SUFFIX);
            boolean teardown = name.endsWith(TEARDOWN_SUFFIX);
            if (!temporary && !claimed && !record && !teardown) continue;
            boolean stale = temporary || claimed;
            if (record) {
                long modified = file.lastModified();
                stale = modified <= 0L || modified > now || now - modified > OWNER_RECORD_TTL_MS ||
                        read(context, file) == null;
            }
            if (teardown) {
                TeardownGrant grant = readTeardownGrant(file);
                long age = grant == null ? -1L : SystemClock.elapsedRealtime() - grant.issuedAt;
                stale = age < 0L || age > TEARDOWN_GRANT_TTL_MS;
            }
            if (stale && file.exists() && !file.delete()) return false;
        }
        return true;
    }

    /** Called only while holding the cross-process lock, so any remaining claim is abandoned. */
    private static boolean clearAbandonedClaim(File claimed) {
        return !claimed.exists() || claimed.delete();
    }

    static void putExpectedDeath(Intent intent, FrameStreamIdentity identity) {
        intent.putExtra(EXTRA_DEATH_SESSION, identity.sessionId);
        intent.putExtra(EXTRA_DEATH_TYPE, identity.streamType);
        intent.putExtra(EXTRA_DEATH_CONNECTION, identity.connectionId);
        intent.putExtra(EXTRA_DEATH_GENERATION, identity.streamGeneration);
        intent.putExtra(EXTRA_DEATH_OUTPUT, identity.outputId);
    }

    static FrameStreamIdentity expectedDeathFrom(Intent intent) {
        if (intent == null || !intent.hasExtra(EXTRA_DEATH_SESSION)) return null;
        FrameStreamIdentity identity = new FrameStreamIdentity(
                intent.getLongExtra(EXTRA_DEATH_SESSION, -1L),
                intent.getIntExtra(EXTRA_DEATH_TYPE, -1),
                intent.getLongExtra(EXTRA_DEATH_CONNECTION, -1L),
                intent.getLongExtra(EXTRA_DEATH_GENERATION, -1L),
                intent.getIntExtra(EXTRA_DEATH_OUTPUT, -1));
        return identity.isValid() && identity.streamType == FrameStreamIdentity.TYPE111 ? identity : null;
    }

    static synchronized boolean hasPending(Context context, FrameStreamIdentity expectedDeath) {
        if (context == null || expectedDeath == null) return false;
        OwnershipLock ownershipLock = acquire(context);
        if (ownershipLock == null) return false;
        try {
            File directory = context.getFilesDir();
            if (!pruneAbandonedArtifacts(context, directory)) return false;
            File record = sessionFile(directory, expectedDeath.sessionId, RECORD_SUFFIX);
            File claimed = sessionFile(directory, expectedDeath.sessionId, ".claimed");
            if (!clearAbandonedClaim(claimed)) return false;
            Record decoded = read(context, record);
            return decoded != null && decoded.expectedType111Death.equals(expectedDeath);
        } finally {
            ownershipLock.close();
        }
    }

    static synchronized boolean issue(Context context, FrameStreamIdentity identity,
            FrameStreamIdentity expectedType111Death, long lastFrameId, int sinkPid) {
        if (context == null || identity == null || !identity.isValid() ||
                identity.streamType != FrameStreamIdentity.TYPE110 || expectedType111Death == null ||
                !expectedType111Death.isValid() ||
                expectedType111Death.streamType != FrameStreamIdentity.TYPE111 ||
                identity.sessionId != expectedType111Death.sessionId || lastFrameId < 0 || sinkPid <= 0 ||
                !isAuthorizedSessionOwnerProcess(context, android.os.Process.myPid()))
            return false;
        OwnershipLock ownershipLock = acquire(context);
        if (ownershipLock == null) return false;
        File directory = context.getFilesDir();
        File temporary = sessionFile(directory, identity.sessionId, ".tmp");
        File record = sessionFile(directory, identity.sessionId, RECORD_SUFFIX);
        File claimed = sessionFile(directory, identity.sessionId, ".claimed");
        DataOutputStream output = null;
        try {
            if (!pruneAbandonedArtifacts(context, directory)) return false;
            // Under the OS lock, a claim left behind is from a process that has exited.
            if (!clearAbandonedClaim(claimed)) return false;
            // Same-session duplicate issuance is rejected; different sessions have distinct files.
            if (record.exists()) {
                Record existing = read(context, record);
                if (existing != null || !record.delete()) return false;
            }
            int pending = pendingOwnerCount(directory);
            if (pending < 0 || pending >= MAX_PENDING_OWNERS) return false;
            if (temporary.exists() && !temporary.delete()) return false;
            output = new DataOutputStream(new FileOutputStream(temporary, false));
            output.writeInt(MAGIC);
            output.writeInt(VERSION);
            writeIdentity(output, expectedType111Death);
            output.writeLong(identity.sessionId);
            output.writeInt(identity.streamType);
            output.writeLong(identity.connectionId);
            output.writeLong(identity.streamGeneration);
            output.writeInt(identity.outputId);
            output.writeLong(lastFrameId);
            output.writeInt(sinkPid);
            output.flush();
            output.close();
            output = null;
            if (record.exists()) return false;
            return temporary.renameTo(record);
        } catch (Exception failure) {
            return false;
        } finally {
            if (output != null) try { output.close(); } catch (Exception ignored) { }
            if (temporary.exists()) temporary.delete();
            ownershipLock.close();
        }
    }

    /** Atomically claims only the record matching this exact Binder death identity. */
    static synchronized Record consume(Context context, FrameStreamIdentity expectedDeath) {
        if (context == null || expectedDeath == null || !expectedDeath.isValid() ||
                expectedDeath.streamType != FrameStreamIdentity.TYPE111) return null;
        OwnershipLock ownershipLock = acquire(context);
        if (ownershipLock == null) return null;
        File directory = context.getFilesDir();
        File record = sessionFile(directory, expectedDeath.sessionId, RECORD_SUFFIX);
        File claimed = sessionFile(directory, expectedDeath.sessionId, ".claimed");
        try {
            if (!pruneAbandonedArtifacts(context, directory)) return null;
            if (!clearAbandonedClaim(claimed) || !record.renameTo(claimed)) return null;
            Record decoded = read(context, claimed);
            if (decoded == null) {
                claimed.delete();
                return null;
            }
            if (expectedDeath == null || !decoded.expectedType111Death.equals(expectedDeath)) {
                if (!record.exists()) claimed.renameTo(record);
                else claimed.delete();
                return null;
            }
            if (!claimed.delete()) return null;
            // The short-lived progress probe is allowed to finish this owned lab session.
            // Bind the one-use grant to the exact session identity and its process PID.
            return decoded;
        } finally {
            ownershipLock.close();
        }
    }

    private static final class TeardownGrant {
        final FrameStreamIdentity identity;
        final int pid;
        final long issuedAt;
        TeardownGrant(FrameStreamIdentity identity, int pid, long issuedAt) {
            this.identity = identity; this.pid = pid; this.issuedAt = issuedAt;
        }
    }

    /** The caller already holds the cross-process OS file lock while issuing this grant. */
    private static boolean issueTeardownGrant(Context context, Record record) {
        if (context == null || record == null ||
                !isType110ProbeProcess(context, android.os.Process.myPid())) return false;
        File directory = context.getFilesDir();
        File temporary = sessionFile(directory, record.identity.sessionId, ".teardown.tmp");
        File target = sessionFile(directory, record.identity.sessionId, TEARDOWN_SUFFIX);
        DataOutputStream output = null;
        try {
            if (target.exists() || temporary.exists()) return false;
            output = new DataOutputStream(new FileOutputStream(temporary, false));
            output.writeInt(MAGIC); output.writeInt(VERSION);
            writeIdentity(output, record.identity);
            output.writeInt(android.os.Process.myPid());
            output.writeLong(SystemClock.elapsedRealtime());
            output.flush(); output.close(); output = null;
            return temporary.renameTo(target);
        } catch (Exception failure) { return false; }
        finally {
            if (output != null) try { output.close(); } catch (Exception ignored) { }
            if (temporary.exists()) temporary.delete();
        }
    }

    /** Accepts a grant only from the compositor-authorized probe Binder transaction. */
    static boolean issueTeardownGrantAuthorized(Context context, Record record) {
        if (context == null || record == null ||
                !isType110ProbeProcess(context, android.os.Process.myPid())) return false;
        OwnershipLock ownershipLock = acquire(context);
        if (ownershipLock == null) return false;
        try { return issueTeardownGrant(context, record); }
        finally { ownershipLock.close(); }
    }

    /** Atomically consumes the exact process-bound teardown grant for a recovered Type110 probe. */
    static synchronized boolean consumeTeardownGrant(Context context, FrameStreamIdentity identity,
            int callerPid) {
        if (context == null || identity == null || !identity.isValid() ||
                identity.streamType != FrameStreamIdentity.TYPE110 || callerPid <= 0 ||
                !isType110ProbeProcess(context, callerPid)) return false;
        OwnershipLock ownershipLock = acquire(context);
        if (ownershipLock == null) return false;
        try {
            File grantFile = sessionFile(context.getFilesDir(), identity.sessionId, TEARDOWN_SUFFIX);
            TeardownGrant grant = readTeardownGrant(grantFile);
            if (grant == null || !identity.equals(grant.identity) || grant.pid != callerPid) return false;
            long age = SystemClock.elapsedRealtime() - grant.issuedAt;
            if (age < 0L || age > TEARDOWN_GRANT_TTL_MS) {
                grantFile.delete();
                return false;
            }
            return grantFile.delete();
        } finally { ownershipLock.close(); }
    }

    private static TeardownGrant readTeardownGrant(File source) {
        if (source == null || !source.isFile()) return null;
        DataInputStream input = null;
        try {
            input = new DataInputStream(new FileInputStream(source));
            if (input.readInt() != MAGIC || input.readInt() != VERSION) return null;
            FrameStreamIdentity identity = readIdentity(input);
            int pid = input.readInt(); long issuedAt = input.readLong();
            if (input.read() != -1 || !identity.isValid() ||
                    identity.streamType != FrameStreamIdentity.TYPE110 || pid <= 0 || issuedAt < 0L)
                return null;
            return new TeardownGrant(identity, pid, issuedAt);
        } catch (Exception malformed) { return null; }
        finally { if (input != null) try { input.close(); } catch (Exception ignored) { } }
    }

    private static boolean isType110ProbeProcess(Context context, int pid) {
        return hasProcessName(context, pid, context == null ? null :
                context.getPackageName() + ":type110_probe");
    }

    private static boolean isAuthorizedSessionOwnerProcess(Context context, int pid) {
        if (context == null) return false;
        String processName = processNameForPid(context, pid);
        return (context.getPackageName() + ":type111_view").equals(processName) ||
                (context.getPackageName() + ":owner_test").equals(processName);
    }

    private static boolean hasProcessName(Context context, int pid, String expected) {
        return expected != null && expected.equals(processNameForPid(context, pid));
    }

    private static String processNameForPid(Context context, int pid) {
        if (context == null || pid <= 0) return null;
        android.app.ActivityManager manager = (android.app.ActivityManager)
                context.getSystemService(Context.ACTIVITY_SERVICE);
        if (manager == null) return null;
        java.util.List<android.app.ActivityManager.RunningAppProcessInfo> processes =
                manager.getRunningAppProcesses();
        if (processes == null) return null;
        for (android.app.ActivityManager.RunningAppProcessInfo process : processes)
            if (process.pid == pid && process.uid == android.os.Process.myUid())
                return process.processName;
        return null;
    }

    private static Record read(Context context, File source) {
        if (context == null || source == null || !source.isFile()) return null;
        DataInputStream input = null;
        try {
            input = new DataInputStream(new FileInputStream(source));
            if (input.readInt() != MAGIC || input.readInt() != VERSION) return null;
            FrameStreamIdentity expectedDeath = readIdentity(input);
            FrameStreamIdentity identity = readIdentity(input);
            long lastFrameId = input.readLong();
            int sinkPid = input.readInt();
            if (input.read() != -1 || !identity.isValid() || identity.streamType != FrameStreamIdentity.TYPE110 ||
                    !expectedDeath.isValid() || expectedDeath.streamType != FrameStreamIdentity.TYPE111 ||
                    identity.sessionId != expectedDeath.sessionId || lastFrameId < 0 || sinkPid <= 0)
                return null;
            return new Record(identity, expectedDeath, lastFrameId, sinkPid);
        } catch (Exception malformed) {
            return null;
        } finally {
            if (input != null) try { input.close(); } catch (Exception ignored) { }
        }
    }

    private static void writeIdentity(DataOutputStream output, FrameStreamIdentity identity)
            throws Exception {
        output.writeLong(identity.sessionId);
        output.writeInt(identity.streamType);
        output.writeLong(identity.connectionId);
        output.writeLong(identity.streamGeneration);
        output.writeInt(identity.outputId);
    }

    private static FrameStreamIdentity readIdentity(DataInputStream input) throws Exception {
        return new FrameStreamIdentity(input.readLong(), input.readInt(), input.readLong(),
                input.readLong(), input.readInt());
    }
}
