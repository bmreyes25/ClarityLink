# R6D Honda configured I²C address

`j_config.xml` configures `/dev/i2c-2` and `0x10`. In `os_auth_cp_obtain`, `jos_config_get_uint32_value` fills the stack value, `open` creates the fd at `0x27bec2`, and `ldr r2, [sp,#8]` at `0x27bed2` passes that configured value unchanged to `ioctl` at `0x27bed6` with command `0x703` loaded at `0x27bece`.

The authoritative [Linux I²C userspace interface](https://docs.kernel.org/5.10/i2c/dev-interface.html) and [UAPI header](https://github.com/torvalds/linux/blob/master/include/uapi/linux/i2c-dev.h) identify `0x0703` as `I2C_SLAVE`, whose argument is a 7-bit address. Thus `R6D_HONDA_I2C_ADDRESS_7BIT_CONFIRMED` for preserved code and configuration. Runtime hardware behavior was not observed; no address conversion or device access code was written.
