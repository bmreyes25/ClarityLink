# R5C public artifact acquisition gate

An R5C artifact may be acquired for static analysis only when all conditions hold: the source is public without authentication or access-control circumvention; the original publisher and chain of custody are documented; vehicle/build relevance is established; access and analysis terms are reviewable; local storage is ignored under `.local-artifacts/r5c/`; SHA256, byte size, filename, URL, and date are recorded; and the raw payload is never committed. No executable from a package may be run. The R5B Type111 static checklist applies only after a receiver component is found.

`PROVENANCE_STRONG` or justified `PROVENANCE_MODERATE` is necessary, but not sufficient, for acquisition. A forum filename, anonymous mirror, dealer-only download, vehicle-specific query, or research note without its source package is `RESEARCH_METADATA_ONLY`. An official bulletin about a package proves the bulletin's version/compatibility claims; it does not authenticate a copy offered elsewhere. No fabricated VIN or vehicle-generated portal metadata may be used.

**R5C gate result:** no candidate met the acquisition conditions. No firmware, archive, receiver binary, or private payload was downloaded or analyzed. Artifact SHA256 and receiver inventory are therefore `N/A`; Type111 remains `UNKNOWN`.
