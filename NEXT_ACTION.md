# Next action

Create a fully synthetic ScreenStream integration fixture from generated H.264: derive synthetic VideoConfig and AVCC length-prefix fields, then test ScreenStream parsing → Annex-B extraction → FFmpeg decode → mock Display 1 rendering. Step 42I already validated a separate in-memory FFmpeg 9.0.2/libx264 → RGBA → renderer path; do not treat it as Honda wire evidence. Keep Honda Type111 framing/KDF, jmcs integration, and ExternalDisplay handoff unknown; live Type111, jmcs no-op, and ExternalDisplay tests remain NOT READY. See `step-reports/42i-real-synthetic-h264-decode.md`.
