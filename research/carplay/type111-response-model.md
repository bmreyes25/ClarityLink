# Type-111 response model

## Honda

Honda Type 110 appends a dictionary containing `{type: 110, dataPort: assignedPort}`. Honda's Type-111 branch skips the request entry; no Honda Type-111 response schema is implemented or proven. Thus `{type:111,dataPort}` is only a candidate analogue.

## Pinned MHI2 implementation

At commit `c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c`, `append_alt_setup_response` clones the exact requested Type-111 dictionary, sets `dataPort` to the project listener port, sets `streamID=111`, and appends the clone to a mutable copy of stock's `streams` array. Because the input descriptor is cloned, `type=111` and unknown peer keys survive. Existing stock entries/order are retained.

The offline implementation models that prior-art response shape only, clearly labeled non-Honda proof. It leaves Honda's response copy unchanged on invalid descriptor, allocation/merge failure, or project listener/security failure.

```python
# Synthetic MHI2-compatible fixture, not Honda-confirmed wire schema
{
    "type": 111, "streamConnectionID": <uint64>,
    "dataPort": <project-port>, "streamID": 111,
    # opaque request fields copied unchanged
}
```
