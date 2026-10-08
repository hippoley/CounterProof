# CSOAI claim_watch external Merkle replay

CounterProof pins one public external batch from:

- repository: `CSOAI-ORG/councilof-ai`
- commit: `85df6bc2ed76450c171d6982bfd39e94d80982d2`
- path: `public/measurement-capsules/v0.2/claim_watch/leaves.json`

The published batch contains one capsule id:

`007b0e5ccbb3f86ac587d645dd8df74c689765267eadc09736eb58bf8be95314`

Applying the draft's RFC 6962/9162 leaf rule:

`SHA-256(0x00 || capsule_id_bytes)`

reproduces the published Merkle root:

`5e6440b6f9fbccdc2dca66aff3c79c02f649ccb56cd795d0f043b651dd50c32e`

This is a **real external Merkle replay**, not a synthetic fixture.

It is still only a partial result. The gzip capsule bytes are published in the
same upstream directory, but the current connector cannot decode binary
repository content. Until CounterProof recomputes the capsule id from those
published capsule bytes, it must not claim the Measurement Capsule draft's full
independent-batch-reproduction success condition.
