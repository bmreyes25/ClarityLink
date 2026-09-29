# Display-B response fixture

This is a structured offline model only. It is not a Honda wire capture, plist, or serialized packet. Fixture-only identity and port labels make preservation assertions executable; they are placeholders, not recovered Honda values. Unknown Honda fields stay explicitly marked.

Files: [fixture JSON](display-b-fixture.json) and [preservation tests](../../tests/carplay-session-model/test_display_b_fixture.py).

The model has a stock primary stream entry (`type=110`, symbolic primary port), and an augmented version that preserves that entry and appends one symbolic secondary entry (`type=111`, prior-art analog; symbolic ClarityLink port). It separately records local Honda geometry as 800×480 / 30 FPS / hifi touch and physical 153×92 mm; descriptor mapping remains unknown. Primary and secondary UUIDs are distinct synthetic tokens solely to test the uniqueness invariant.

Because values of the Honda primary UUID, primary `dataPort`, and all secondary fields are not recovered, passing the fixture tests proves only model preservation behavior. It does not prove Honda supports multiple displays, Type 111, or ClarityLink negotiation.
