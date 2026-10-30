/*
 * Offline experiment template for the two jmcs stock-call boundaries.
 *
 * These functions call only the original stock routine. They do not inspect
 * or mutate /info or SETUP data and do not provide Type111 support. The
 * isolated-copy rewriter lays down the corresponding 8-byte instruction
 * sequences and encodes each same-image Thumb BL after a unique executable
 * cave has been proven. This source documents the ABI sequence used there.
 */
.syntax unified
.thumb

.macro stock_passthrough name, target
    .global \name
    .type \name, %function
    .thumb_func
\name:
    b.w \target
    .size \name, .-\name
.endm

stock_passthrough claritylink_info_stock_passthrough, AirPlayCopyServerInfo
stock_passthrough claritylink_setup_serializer_stock_passthrough, _requestSendPlistResponse
