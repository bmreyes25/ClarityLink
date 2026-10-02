/*
 * Standalone ARMv7 Thumb shim for offline Unicorn execution only.
 * It is not linked to jmcs, does not contain Honda patch bytes, and cannot be
 * used as an installation payload. The callsite frame offsets mirror the
 * hash-verified static caller frame recorded in the 43N/43S reports.
 */
.syntax unified
.cpu cortex-a9
.thumb
.text
.align 2
.global shim_entry
.type shim_entry,%function
.thumb_func
shim_entry:
    /* Snapshot the incoming caller SP before the first stack adjustment. */
    mov     r12, sp
    push.w  {r4-r11, lr}
    sub     sp, #4                  /* preserve AAPCS 8-byte call alignment */
    sub     sp, #64
    sub     sp, #64                 /* wire context plus caller-owned txn storage */
    str     r12, [sp, #0]           /* original_sp */
    str     r0,  [sp, #20]          /* serializer_r0 */
    str     r1,  [sp, #24]          /* serializer_r1 */
    str     r2,  [sp, #28]          /* serializer_r2 */
    str     r3,  [sp, #32]          /* serializer_r3 */

    /* Caller-frame values always use the saved pre-prologue SP. */
    ldr     r5, [r12, #0x1c]
    str     r5, [sp, #4]            /* request */
    ldr     r5, [r12, #0x54]
    str     r5, [sp, #8]            /* response */
    mov     r5, r3                  /* proven serializer statusOut pointer */
    str     r5, [sp, #12]           /* status_out */
    add     r5, r12, #0x50
    str     r5, [sp, #44]           /* expected callsite statusOut address */
    add     r5, sp, #64
    str     r5, [sp, #48]           /* caller-owned ClPreparedTxn storage */
    movs    r5, #0
    cmp     r10, #0
    beq     1f
    ldr     r5, [r10, #0xf4]
1:  str     r5, [sp, #16]           /* session; null r10 is safely absent */

    mov     r7, sp                  /* context is callee-saved across helpers */
    mov     r0, r7
    bl      project_prepare         /* returns 1 only for prepared Type111 */
    str     r0, [r7, #36]           /* prepare result */

    /* Preserve serializer args in context; restore immediately before BL. */
    ldr     r0, [r7, #20]
    ldr     r1, [r7, #24]
    ldr     r2, [r7, #28]
    ldr     r3, [r7, #32]
    bl      stock_serializer       /* exactly one stock call; never retried */
    str     r0, [r7, #40]           /* serializer_r0 */
    mov     r4, r0                  /* preserve stock r0 over project completion */

    /* Commit is impossible when preparation failed or statusOut is NULL. */
    ldr     r1, [r7, #36]
    cmp     r1, #1
    bne     2f
    ldr     r0, [r7, #12]
    cmp     r0, #0
    beq     2f
    ldr     r1, [r7, #44]
    cmp     r0, r1
    bne     2f
    ldr     r1, [r7, #40]
    cmp     r1, #0xc8
    bne     2f
    ldr     r0, [r7, #12]
    ldr     r1, [r0]
    cmp     r1, #0
    bne     2f
    movs    r0, #1                  /* eligible for project commit */
    b       3f
2:  movs    r0, #0                  /* project rollback */
3:  mov     r1, r7
    bl      project_finish
    str     r0, [r7, #52]           /* preserve project cleanup status */

    mov     r0, r4                  /* exact stock return value */
    add     sp, #64
    add     sp, #64
    add     sp, #4
    pop.w   {r4-r11, pc}            /* saved LR returns to 0x28afbf state */
.size shim_entry, .-shim_entry

/* The stock serializer is an external Honda-call boundary in the harness. */
.global stock_serializer
.thumb_func
stock_serializer:
    push    {r4, lr}
    sub     sp, #64
    add     sp, #64
    pop     {r4, pc}
