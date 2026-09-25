import com.android.apksig.ApkSigner;
import com.android.apksig.ApkVerifier;
import java.io.File;
import java.io.FileInputStream;
import java.security.KeyStore;
import java.security.PrivateKey;
import java.security.cert.X509Certificate;
import java.util.Collections;

/** Local build helper; signs one diagnostic APK for Android API 17. */
public final class SignDiagnosticApk {
    public static void main(String[] args) throws Exception {
        if (args.length != 4) throw new IllegalArgumentException("input output keystore alias");
        char[] password = "android".toCharArray(); // Local disposable diagnostic key only.
        KeyStore store = KeyStore.getInstance("JKS");
        FileInputStream source = new FileInputStream(args[2]);
        try { store.load(source, password); } finally { source.close(); }
        PrivateKey key = (PrivateKey) store.getKey(args[3], password);
        X509Certificate certificate = (X509Certificate) store.getCertificate(args[3]);
        ApkSigner.SignerConfig signer = new ApkSigner.SignerConfig.Builder(
            "clarity-diagnostic", key, Collections.singletonList(certificate)).build();
        File output = new File(args[1]);
        new ApkSigner.Builder(Collections.singletonList(signer))
            .setInputApk(new File(args[0])).setOutputApk(output)
            .setMinSdkVersion(17).setV1SigningEnabled(true).setV2SigningEnabled(false)
            .build().sign();
        ApkVerifier.Result result = new ApkVerifier.Builder(output)
            .setMinCheckedPlatformVersion(17).build().verify();
        if (!result.isVerified()) throw new IllegalStateException("APK signature verification failed");
        System.out.println("APK v1 signature verified for API 17: " + output);
    }
}
