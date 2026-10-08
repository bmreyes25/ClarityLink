# R7C audio and input boundary

`AndroidAudioAdapter` uses `AudioTrack` stream mode with bounded PCM writes, format validation, pause/resume/flush/close. Android selects routing; no Honda mixer is named. A host memory backend and stock-equivalent media, navigation prompts, Siri, calls, volume, mute, and teardown still need validation.

`InputBridge` carries source/type/code/value/timestamp/generation and accepts only configured allowlist tuples. Empty Honda default rejects every event. Touch, steering, rotary, and Siri mappings are unassigned pending evidence. Unknown events may be diagnosed without identifiers, never guessed into actions.
