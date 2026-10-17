# Offline quickstart

This quickstart runs the synthetic visual twin on your computer. It does not connect to a vehicle, phone, or CarPlay session and does not demonstrate Honda behavior.

## Requirements

- Python 3
- A web browser

## Run the demo

From the repository root:

```sh
python3 src/claritylink-sim/export_visual_demo.py --screenstream-h264
python3 -m http.server 8000 --bind 127.0.0.1 --directory demo/type111
```

Open `http://localhost:8000` and select **Hypothetical Type111**. The fixture and output are synthetic.

To run the configured offline checks, follow [development and testing](../development/testing.md). Do not use an emulator or vehicle as part of this quickstart.
