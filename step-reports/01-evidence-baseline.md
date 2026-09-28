# Step 1 — Evidence baseline and repository normalization

**Status: complete for the requested small allowlist.** This inventory names the copied files selected for the next focused examination. It does not decompile them or scan the full forensic image.

## Source and preservation

The analysis source is the local extracted vendor tree at `extracted/system-vendor/`. Its selected relative paths correspond to the head-unit paths shown below. The completed forensic acquisition is referenced at `/Users/bmreyes24/ClarityLab/forensic/CLARITY_FORENSIC_20260925_211500_COMPLETE_WORKING`; this step did not read or write its raw image or change either forensic copy. The immutable original is `/Users/bmreyes24/ClarityLab/forensic/CLARITY_FORENSIC_20260925_211500_COMPLETE_ORIGINAL` (directory has no write bits), and the older pristine backup is `/Users/bmreyes24/ClarityLab/backups/CLARITY_BACKUP_20260918_0225_ORIGINAL` (directory has no write bits). No firmware binaries, raw images, APKs, ODEX files, or archives were staged.

SHA-256 values below were calculated on the named allowlisted extracted files for reproducibility. They are fingerprints, not a claim that the extracted tree is itself the acquisition original. Raw firmware stays local and ignored by Git.

## Allowlisted artifact inventory

| Head-unit path | Local analysis path (relative to repo) | Bytes | SHA-256 | Why it matters |
|---|---|---:|---|---|
| `/system/vendor/app/CarPlay.apk` | `extracted/system-vendor/system/vendor/app/CarPlay.apk` | 199,341 | `0166a751900b285fd86715dc3b74606d0da35453ce9b3843e9edaab6bcadd828` | Receiver app package and manifest/resources; likely Java-side entry points. |
| `/system/vendor/app/CarPlay.odex` | `extracted/system-vendor/system/vendor/app/CarPlay.odex` | 103,048 | `d0b643708ce7ce8bd2bd51e387c8f1d12f99eb5fe16a3d5f32c97b445b6f0421` | Android 4.2 optimized app code paired with CarPlay.apk. |
| `/system/vendor/app/CarPlayService.apk` | `extracted/system-vendor/system/vendor/app/CarPlayService.apk` | 3,922 | `a81f9e6431cd370059d10ec8827b92d91b74d7dc5357959bb30c948993dca89e` | Service package/manifest that binds the receiver service. |
| `/system/vendor/app/CarPlayService.odex` | `extracted/system-vendor/system/vendor/app/CarPlayService.odex` | 371,456 | `cb8cef4ef5f209d74efdb04ed58c1efb9e6a2742c1a8f331f123d9e55449a0ae` | Optimized service implementation. |
| `/system/vendor/app/ExternalDisplayOutService.apk` | `extracted/system-vendor/system/vendor/app/ExternalDisplayOutService.apk` | 3,690,934 | `2b29800dc1c1e524e096c0b1d37ce1c109e5a815a067a1a1ce59621e0c2f97e5` | Android external-output service; relevant to the HDMI/cluster rendering destination and navigation output. |
| `/system/vendor/app/ExternalDisplayOutService.odex` | `extracted/system-vendor/system/vendor/app/ExternalDisplayOutService.odex` | 1,551,064 | `de1e56a98d279537374b8b092d3355896ed18490364ddcd086277901afe12bb4` | Optimized output-service implementation. |
| `/system/vendor/app/ExternalDisplayApService.apk` | `extracted/system-vendor/system/vendor/app/ExternalDisplayApService.apk` | 5,922 | `0167100294e8fa60a3cad9d761040687c22a58825044e3c19c1a5560da761d3f` | External-display app-service binder package/manifest. |
| `/system/vendor/app/ExternalDisplayApService.odex` | `extracted/system-vendor/system/vendor/app/ExternalDisplayApService.odex` | 96,640 | `4d539587578b87b54b47311f790113a868034c306f7e5a957bd20ea305b73d80` | Optimized external-display app-service logic. |
| `/system/vendor/app/Navigation.apk` | `extracted/system-vendor/system/vendor/app/Navigation.apk` | 4,894 | `774d43a2efd6ccfe45528688b2262513677f56b94300a6bc3a3fa8dc38b15881` | Honda navigation app-service package/manifest and native navigation UI entry point. |
| `/system/vendor/app/Navigation.odex` | `extracted/system-vendor/system/vendor/app/Navigation.odex` | 546,664 | `88ed9c4c07e6beff5b9f3ae24748ce50ff80f3b4baabbb4f8ee6a6ebb94b6789` | Optimized navigation service implementation. |
| `/system/vendor/framework/CarPlayApServiceApiLib.jar` | `extracted/system-vendor/system/vendor/framework/CarPlayApServiceApiLib.jar` | 313 | `785022cbf56f737453166cdba357a3526813a0770cded2a40820799bb1fa08b8` | CarPlay app-service API class container; paired ODEX carries code. |
| `/system/vendor/framework/CarPlayApServiceApiLib.odex` | `extracted/system-vendor/system/vendor/framework/CarPlayApServiceApiLib.odex` | 93,616 | `526031de8d0819b463f91d2e55bcbc2d7dd6afc871e63f5fac314d80ee8f5d24` | Optimized CarPlay API classes used by framework clients. |
| `/system/vendor/framework/HondaNavigationLib.jar` | `extracted/system-vendor/system/vendor/framework/HondaNavigationLib.jar` | 313 | `1dc97d9d7474ac644ffbbbc22f2212294add0b0cd2dbdb7bc1467af2f2797296` | Shared Honda navigation API class container. |
| `/system/vendor/framework/HondaNavigationLib.odex` | `extracted/system-vendor/system/vendor/framework/HondaNavigationLib.odex` | 138,480 | `d9c1101b1e3ebaf6925aeb808e70e22dfc3df46ce1ccae26a2e0659491d82035` | Optimized Honda navigation API, including candidate native cluster guidance interfaces. |
| `/system/vendor/framework/HondaNavigationNaviLib.jar` | `extracted/system-vendor/system/vendor/framework/HondaNavigationNaviLib.jar` | 313 | `ef476e4659fe757bce26b06e7cde6fd3015def7b47468c0e9b0a16770f623647` | Navigation-specific Honda API class container. |
| `/system/vendor/framework/HondaNavigationNaviLib.odex` | `extracted/system-vendor/system/vendor/framework/HondaNavigationNaviLib.odex` | 20,944 | `20b5861c0d2cf2701446a2d8c856458cf6bc14790ac698a7c407e7ca114d0398` | Optimized navigation-specific API logic. |
| `/system/vendor/framework/NavigationLib.jar` | `extracted/system-vendor/system/vendor/framework/NavigationLib.jar` | 313 | `1dc97d9d7474ac644ffbbbc22f2212294add0b0cd2dbdb7bc1467af2f2797296` | Shared navigation API class container. |
| `/system/vendor/framework/NavigationLib.odex` | `extracted/system-vendor/system/vendor/framework/NavigationLib.odex` | 181,576 | `cbf7b0f2629d6a5625d663ba2641cf46dfcac04e7e3b86dc617535511bc692fa` | Optimized navigation service APIs. |
| `/system/vendor/framework/ExternalDisplayLib.jar` | `extracted/system-vendor/system/vendor/framework/ExternalDisplayLib.jar` | 313 | `b3616e9db9e40e1de8ee6c4cc037e475932f8b1ee329885d340544f12715c564` | Shared external-display API class container. |
| `/system/vendor/framework/ExternalDisplayLib.odex` | `extracted/system-vendor/system/vendor/framework/ExternalDisplayLib.odex` | 64,248 | `d33118435bd3ad30d058d231b8be7979b92f754f77fb1a52176710b60cebf5a2` | Optimized external-display API implementation. |
| `/system/bin/cluster` | `extracted/system-vendor/system/bin/cluster` | 37 | `4b988eb7538bd52e9ce34ad20842607e3fc0997d11cadc1938f4efebc2b76ae2` | Small cluster control wrapper; inspect exact command semantics before attributing transport. |
| `/system/bin/cluster_set.sh` | `extracted/system-vendor/system/bin/cluster_set.sh` | 50 | `9a90cbe21cb7e94aeb82ecd556b716442dad6556004e11f1d89d05fba077c149` | Cluster set helper; candidate endpoint for display-link setup. |
| `/system/bin/cluster_get.sh` | `extracted/system-vendor/system/bin/cluster_get.sh` | 44 | `5ba7120e7d1fbf45a1e26b32d2163dc3ed480c0bf53df36d0320f81fc70aa1b0` | Cluster get helper; candidate endpoint for display-link state. |
| `/system/vendor/bin/disp_com_meter` | `extracted/system-vendor/system/vendor/bin/disp_com_meter` | 22,740 | `9269955480bdd5b16ea90e04d0643acaf2c97f2a1dfcaaa97e6a2558a31e1f5f` | Meter display communication executable; central to any Android-to-cluster output path. |
| `/system/lib/libcarplay_proxy.so` | `extracted/system-vendor/system/lib/libcarplay_proxy.so` | 53,156 | `dc8bc5c19cf32a8e7edcc14c1d80e78bb96ca6ccc434229349c74590136bef66` | Native CarPlay screen/audio callback boundary between receiver and Honda-side implementation. |

## Repository baseline and next examination set

At inventory time, `main` was clean and matched `origin/main` at `f9de18c07895d9b07d37d4039328e14ab695b1ce`. The repository ignore rules exclude extracted firmware, APK/ODEX/native binaries, images, archives and build artifacts. Step 2 will inspect layout/output evidence, Step 3 will test offline decoding behavior and relate it to the already-observed car test, and Step 4 will inspect only the main-screen setup/advertisement path in `jmcs` and its proxy. No wider archive scan or broad decompilation is needed to begin those tasks.
