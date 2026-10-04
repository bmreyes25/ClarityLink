# R5Y — synthetic Setup transaction engine

`ReceiverCore.setup` wraps an immutable `SetupResponse` in `SetupTransaction`. It validates the synthetic session/primary descriptor, captures the Type110 oracle, then either commits the original response or conditionally prepares a child. The optional child requires both `request_secondary` and `enable_secondary` in the typed request. The model never interprets Honda Setup objects or invokes a wire serializer.

For the secondary branch, the manager reserves one generation, then allocates an integer-only listener label, initializes a marker-only security context, creates a symbolic decoder and display sink, builds a frozen synthetic response candidate, checks primary preservation, and commits once. Failure at any named preparation/commit point calls exact-generation cleanup, aborts the transaction, restores the original response object, and returns to `PRIMARY_READY`. The response tuple is frozen after commit; aborting a committed transaction raises. Aborting an uncommitted transaction twice is safe.

The transaction is **atomic only in the host model**. It cannot establish Honda object ownership, serializer behavior, actual listener creation, or response acceptance. See the [preservation oracle](r5y-type110-preservation-oracle.md) and [evidence registry](r5y-honda-evidence-gap-registry.md).
