# jmcs init service evidence

**Source:** preserved Honda `boot.img` ramdisk `/init.vcm30t30.rc`; matching copy in `root-startup.tar`. Full import closure and artifact hashes are documented in [the Step 41C report](../../step-reports/41c-jmcs-init-service.md).

```rc
service jmcs /system/bin/jmcs
    class main
    user root
    group root
```

The stanza has no arguments, `disabled`, `oneshot`, `critical`, `setenv`, socket, capabilities, `seclabel`, or `onrestart`. The boot `init.rc` starts `class main`; global `LD_LIBRARY_PATH` is `/vendor/lib:/system/lib`. No `LD_PRELOAD` is currently set. Honda `/init` contains the `setenv option requires name and value arguments` diagnostic, confirming parser support. AOSP 4.2.2 init service grammar documents service `setenv` and the default restart behavior.

**Decision:** a service-scoped preload would require a persistent boot-ramdisk change. This is a design fact, not authorization or readiness to deploy. The current evidence does not prove linker behavior, path mapping, or safe failure behavior.
