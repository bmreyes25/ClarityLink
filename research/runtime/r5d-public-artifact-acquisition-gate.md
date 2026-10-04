# R5D public artifact acquisition gate

Before any payload download, record: original public URL; publisher/source class; no login, VIN, vehicle-generated request, dealer credential, bypass or private API; exact expected model/trim/region/version and filename; access/legal status; and a defensible publisher-to-URL custody chain. An unauthenticated mirror requires an independently authenticated publisher hash or equivalent strong original-source linkage. Filename matching, forum testimony, or a test-key signature alone does not close custody.

**Current gate:** `QUARANTINE_METADATA_ONLY` for all R5D candidates. Honda's US 19-101 package is VIN/dealer selected. The EU `MRC_EU_SW_v12_4.zip` package name is documented in a reproduced bulletin, but its PANEX original is gated and the MediaFire mirror has no authenticated Honda hash or custody proof. No artifact was downloaded, hashed, extracted, or analyzed in R5D.

If a future candidate passes: store outside Git in the ignored local-artifact directory; immediately record URL, retrieval date, bytes, SHA256 and magic/MIME; preserve original read-only; do not redistribute or execute; determine full image versus delta before inferring component absence; inspect only static inventory. No vehicle or target-binary execution is authorized.
