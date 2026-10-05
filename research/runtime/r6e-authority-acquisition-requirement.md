# R6E authority acquisition requirement

Supply a user-owned genuine MFi coprocessor with a documented Mac host bridge, a user-authorized licensed service, or owned hardware with genuine Apple-compliant authentication. Provide proof of authorization and a documented interface that supplies a complete authenticated CarPlay control session to the custom receiver: request read, response write, generation/session identity, authenticated state, bounded timeouts, disconnect and close. A challenge-signing endpoint alone does not close the control handoff.

The authority must retain private credentials and expose only an opaque security reference if needed. It must support a Mac-local or specifically identified private-interface connection and must not require public/wildcard listener exposure. Also provide the chosen transport's actual display/audio/HID and protocol values for /info, with provenance. No Honda hardware or credentials are part of this requirement.
