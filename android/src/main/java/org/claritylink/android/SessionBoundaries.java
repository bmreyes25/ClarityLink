package org.claritylink.android;

/** Explicit lawful provider seams. Default Honda implementations are unavailable. */
public final class SessionBoundaries {
    public interface Iap2Transport { boolean ready(); boolean send(byte[] message,long generation); byte[] receive(int maxBytes,long generation); void close(); }
    public interface Iap2Session { long generation(); boolean open(); void close(); }
    public interface AuthenticationAuthority { boolean authenticate(long generation); boolean genuineAuthority(); }
    public static final class AndroidAuthenticationAdapter implements AuthenticationAuthority {
        private final AuthenticationAuthority provider;
        public AndroidAuthenticationAdapter(AuthenticationAuthority provider) {
            if(provider==null) throw new IllegalArgumentException("authority provider required");
            this.provider=provider;
        }
        public boolean authenticate(long generation) { return generation>0 && provider.authenticate(generation); }
        public boolean genuineAuthority() { return provider.genuineAuthority(); }
        public static AndroidAuthenticationAdapter unavailableHondaDefault() {
            return new AndroidAuthenticationAdapter(new UnavailableHondaAuthenticationAuthority());
        }
    }
    public static final class UnavailableHondaAuthenticationAuthority implements AuthenticationAuthority {
        public boolean authenticate(long generation) { return false; }
        public boolean genuineAuthority() { return false; }
    }
    public static final class UnavailableIap2 implements Iap2Transport {
        public boolean ready() { return false; }
        public boolean send(byte[] message,long generation) { return false; }
        public byte[] receive(int maxBytes,long generation) { return null; }
        public void close() { }
    }
    private SessionBoundaries() {}
}
