"""RFC 6962 conformance tests for `signal_growth.merkle`.

The vectors in this file are not ours. They are copied from the reference
implementation at https://github.com/transparency-dev/merkle, which is
distributed under the Apache License, Version 2.0
(https://www.apache.org/licenses/LICENSE-2.0), Copyright Google LLC:

  * `LEAF_INPUTS` and `ROOT_HASHES` are `LeafInputs()` and `RootHashes()` from
    `testonly/constants.go`.
  * `REFERENCE_CONSISTENCY_PROOFS` are the expected proofs from
    `TestRefConsistencyProof` in `testonly/reference_test.go`.
  * `TESTDATA_CONSISTENCY_CASES` are verbatim cases from `testdata/consistency/`
    (base64 hashes, `wantErr` flag, and `desc` preserved).

Only these data values are reused; the implementation under test is an
independent Python port of the RFC 6962 algorithms, not a translation of the Go
source. Retain this notice if the vectors are moved.

Why pin to an external reference at all: a Merkle implementation that is
self-consistent but non-standard passes every test you write against yourself.
These vectors are the only thing that catches a wrong-but-stable tree shape.
"""

from __future__ import annotations

import base64
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.append_only import chain_records, verify_append_chain
from signal_growth.merkle import (
    MerkleProofError,
    compute_consistency_proof,
    empty_root,
    record_entry,
    records_consistency_proof,
    records_root,
    root_from_entries,
    verify_consistency_proof,
)


# --- Vectors from transparency-dev/merkle (Apache-2.0) ----------------------

# testonly/constants.go: LeafInputs()
LEAF_INPUTS = [
    bytes.fromhex(value)
    for value in (
        "",
        "00",
        "10",
        "2021",
        "3031",
        "40414243",
        "5051525354555657",
        "606162636465666768696a6b6c6d6e6f",
    )
]

# testonly/constants.go: RootHashes(), indexed by tree size starting at 0.
ROOT_HASHES = [
    bytes.fromhex(value)
    for value in (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "6e340b9cffb37a989ca544e6bb780a2c78901d3fb33738768511a30617afa01d",
        "fac54203e7cc696cf0dfcb42c92a1d9dbaf70ad9e621f4bd8d98662f00e3c125",
        "aeb6bcfe274b70a14fb067a5e5578264db0fa9b51af5e0ba159158f329e06e77",
        "d37ee418976dd95753c1c73862b9398fa2a2cf9b4ff0fdfe8b30cd95209614b7",
        "4e3bbb1f7b478dcfe71fb631631519a3bca12c9aefca1612bfce4c13a86264d4",
        "76e67dadbcdf1e10e1b74ddc608abd2f98dfb16fbce75277b5232a127f2087ef",
        "ddb89be403809e325750d3d263cd78929c2942b7942a34b77e122c9594a74c8c",
        "5dc9da79a70659a9ad559cb701ded9a2ab9d823aad2f4960cfe370eff4604328",
    )
]

# testonly/reference_test.go: TestRefConsistencyProof
REFERENCE_CONSISTENCY_PROOFS = [
    (1, 1, []),
    (
        1,
        8,
        [
            "96a296d224f285c67bee93c30f8a309157f0daa35dc5b87e410b78630a09cfc7",
            "5f083f0a1a33ca076a95279832580db3e0ef4584bdff1f54c8a360f50de3031e",
            "6b47aaf29ee3c2af9af889bc1fb9254dabd31177f16232dd6aab035ca39bf6e4",
        ],
    ),
    (
        2,
        5,
        [
            "5f083f0a1a33ca076a95279832580db3e0ef4584bdff1f54c8a360f50de3031e",
            "bc1a0643b12e4d2d7c77918f44e0f4f79a838b6cf9ec5b5c283e1f4d88599e6b",
        ],
    ),
    (
        6,
        8,
        [
            "0ebc5d3437fbe2db158b9f126a1d118e308181031d0a949f8dededebc558ef6a",
            "ca854ea128ed050b41b35ffc1b87b8eb2bde461e9e3b5596ece6b9d5975a0ae0",
            "d37ee418976dd95753c1c73862b9398fa2a2cf9b4ff0fdfe8b30cd95209614b7",
        ],
    ),
]

# testdata/consistency/: one accepted case per directory, plus tampered
# variants of the same trees. Hashes are base64 as published upstream.
TESTDATA_CONSISTENCY_CASES = [
    {
        "size1": 1,
        "size2": 8,
        "root1": "bjQLnP+zepicpUTmu3gKLHiQHT+zNzh2hRGjBhevoB0=",
        "root2": "XcnaeacGWamtVZy3Ad7ZoqudgjqtL0lgz+Nw7/RgQyg=",
        "proof": [
            "lqKW0iTyhcZ77pPDD4owkVfw2qNdxbh+QQt4YwoJz8c=",
            "Xwg/ChozygdqlSeYMlgNs+DvRYS9/x9UyKNg9Q3jAx4=",
            "a0eq8p7jwq+a+Im8H7klTavTEXfxYjLdaqsDXKOb9uQ=",
        ],
        "desc": "happy path",
        "wantErr": False,
    },
    {
        "size1": 6,
        "size2": 8,
        "root1": "duZ9rbzfHhDht03cYIq9L5jfsW+851J3tSMqEn8gh+8=",
        "root2": "XcnaeacGWamtVZy3Ad7ZoqudgjqtL0lgz+Nw7/RgQyg=",
        "proof": [
            "DrxdNDf74tsVi58Sah0RjjCBgQMdCpSfje3t68VY72o=",
            "yoVOoSjtBQtBs1/8G4e46yveRh6eO1WW7Oa51ZdaCuA=",
            "037kGJdt2VdTwcc4Yrk5j6Kiz5tP8P3+izDNlSCWFLc=",
        ],
        "desc": "happy path",
        "wantErr": False,
    },
    {
        "size1": 2,
        "size2": 5,
        "root1": "+sVCA+fMaWzw38tCySodnbr3CtnmIfS9jZhmLwDjwSU=",
        "root2": "Tju7H3tHjc/nH7YxYxUZo7yhLJrvyhYSv85ME6hiZNQ=",
        "proof": [
            "Xwg/ChozygdqlSeYMlgNs+DvRYS9/x9UyKNg9Q3jAx4=",
            "vBoGQ7EuTS18d5GPROD095qDi2z57FtcKD4fTYhZnms=",
        ],
        "desc": "happy path",
        "wantErr": False,
    },
    {
        "size1": 6,
        "size2": 7,
        "root1": "duZ9rbzfHhDht03cYIq9L5jfsW+851J3tSMqEn8gh+8=",
        "root2": "3bib5AOAnjJXUNPSY814kpwpQreUKjS3fhIslZSnTIw=",
        "proof": [
            "DrxdNDf74tsVi58Sah0RjjCBgQMdCpSfje3t68VY72o=",
            "sIaT7C5yFZcTBkHoIR5+7cy0wmQTlj7ubB4u0W/7Gl8=",
            "037kGJdt2VdTwcc4Yrk5j6Kiz5tP8P3+izDNlSCWFLc=",
        ],
        "desc": "happy path",
        "wantErr": False,
    },
    {
        "size1": 6,
        "size2": 8,
        "root1": "XcnaeacGWamtVZy3Ad7ZoqudgjqtL0lgz+Nw7/RgQyg=",
        "root2": "duZ9rbzfHhDht03cYIq9L5jfsW+851J3tSMqEn8gh+8=",
        "proof": [
            "DrxdNDf74tsVi58Sah0RjjCBgQMdCpSfje3t68VY72o=",
            "yoVOoSjtBQtBs1/8G4e46yveRh6eO1WW7Oa51ZdaCuA=",
            "037kGJdt2VdTwcc4Yrk5j6Kiz5tP8P3+izDNlSCWFLc=",
        ],
        "desc": "swapped roots",
        "wantErr": True,
    },
    {
        "size1": 1,
        "size2": 8,
        "root1": "bjQLnP+zepicpUTmu3gKLHiQHT+zNzh2hRGjBhevoB0=",
        "root2": "XcnaeacGWamtVZy3Ad7ZoqudgjqtL0lgz+Nw7/RgQyg=",
        "proof": [
            "lqKW0iTyhcZ77pPDD4owkVfw2qNdxbh+QQt4YwoJz8c=",
            "Xwg/ChozygdqlSeYMlgNs+DvRYS9/x9UyKNg9Q3jAx4=",
        ],
        "desc": "truncated proof",
        "wantErr": True,
    },
    # This case is load-bearing: when size1 is not a power of two, root1 is
    # consulted *only* while rebuilding it from the proof's inner nodes. Drop
    # that rebuild and every other vector here still passes, because the final
    # root2 comparison covers them. This one does not.
    {
        "size1": 6,
        "size2": 8,
        "root1": "V3JvbmdSb290",
        "root2": "XcnaeacGWamtVZy3Ad7ZoqudgjqtL0lgz+Nw7/RgQyg=",
        "proof": [
            "DrxdNDf74tsVi58Sah0RjjCBgQMdCpSfje3t68VY72o=",
            "yoVOoSjtBQtBs1/8G4e46yveRh6eO1WW7Oa51ZdaCuA=",
            "037kGJdt2VdTwcc4Yrk5j6Kiz5tP8P3+izDNlSCWFLc=",
        ],
        "desc": "wrong root1",
        "wantErr": True,
    },
    {
        "size1": 6,
        "size2": 7,
        "root1": "duZ9rbzfHhDht03cYIq9L5jfsW+851J3tSMqEn8gh+8=",
        "root2": "3bib5AOAnjJXUNPSY814kpwpQreUKjS3fhIslZSnTIw=",
        "proof": [
            "DrxdNDf74tsVi58Sah0RjjCBgQMdCpSfje3t68VY72o=",
            "oIaT7C5yFZcTBkHoIR5+7cy0wmQTlj7ubB4u0W/7Gl8=",
            "037kGJdt2VdTwcc4Yrk5j6Kiz5tP8P3+izDNlSCWFLc=",
        ],
        "desc": "modified proof@1 bit @4",
        "wantErr": True,
    },
    {
        "size1": 2,
        "size2": 5,
        "root1": "+sVCA+fMaWzw38tCySodnbr3CtnmIfS9jZhmLwDjwSU=",
        "root2": "V3JvbmdSb290",
        "proof": [
            "Xwg/ChozygdqlSeYMlgNs+DvRYS9/x9UyKNg9Q3jAx4=",
            "vBoGQ7EuTS18d5GPROD095qDi2z57FtcKD4fTYhZnms=",
        ],
        "desc": "wrong root2",
        "wantErr": True,
    },
]

# --- End of vectors from transparency-dev/merkle ----------------------------


def _b64(value: str) -> bytes:
    return base64.b64decode(value)


class Rfc6962HashingTests(unittest.TestCase):
    def test_empty_root_matches_the_published_vector(self) -> None:
        self.assertEqual(ROOT_HASHES[0], empty_root())

    def test_root_of_every_prefix_matches_the_published_vectors(self) -> None:
        for size, want in enumerate(ROOT_HASHES):
            with self.subTest(size=size):
                self.assertEqual(want, root_from_entries(LEAF_INPUTS[:size]))

    def test_leaf_and_node_hashing_are_domain_separated(self) -> None:
        # A one-entry tree hashes its leaf; a two-entry tree hashes a node. If
        # the prefixes were dropped, an attacker could present an internal node
        # as a leaf, so this must not collide.
        self.assertNotEqual(
            root_from_entries([b""]),
            root_from_entries([b"", b""]),
        )


class ReferenceConsistencyProofTests(unittest.TestCase):
    def test_generated_proofs_match_the_reference_implementation(self) -> None:
        for size1, size2, want_hex in REFERENCE_CONSISTENCY_PROOFS:
            with self.subTest(size1=size1, size2=size2):
                self.assertEqual(
                    [bytes.fromhex(value) for value in want_hex],
                    compute_consistency_proof(LEAF_INPUTS, size1, size2),
                )

    def test_every_generated_proof_verifies_against_the_published_roots(self) -> None:
        # Cross-check across all size pairs, not just the published ones: a
        # proof generator and verifier that agree only on hand-picked sizes are
        # agreeing on a bug.
        for size2 in range(1, len(LEAF_INPUTS) + 1):
            for size1 in range(1, size2 + 1):
                with self.subTest(size1=size1, size2=size2):
                    proof = compute_consistency_proof(LEAF_INPUTS, size1, size2)
                    verify_consistency_proof(
                        size1,
                        size2,
                        proof,
                        ROOT_HASHES[size1],
                        ROOT_HASHES[size2],
                    )


class TestdataConsistencyVectorTests(unittest.TestCase):
    def test_published_verification_cases_are_accepted_or_rejected(self) -> None:
        for case in TESTDATA_CONSISTENCY_CASES:
            with self.subTest(
                desc=case["desc"], size1=case["size1"], size2=case["size2"]
            ):
                args = (
                    case["size1"],
                    case["size2"],
                    [_b64(value) for value in case["proof"]],
                    _b64(case["root1"]),
                    _b64(case["root2"]),
                )
                if case["wantErr"]:
                    with self.assertRaises(MerkleProofError):
                        verify_consistency_proof(*args)
                else:
                    verify_consistency_proof(*args)


class ProofArgumentTests(unittest.TestCase):
    def test_proof_from_an_empty_tree_is_refused(self) -> None:
        with self.assertRaises(MerkleProofError):
            compute_consistency_proof(LEAF_INPUTS, 0, 4)
        with self.assertRaises(MerkleProofError):
            verify_consistency_proof(0, 4, [], ROOT_HASHES[0], ROOT_HASHES[4])

    def test_shrinking_tree_is_refused(self) -> None:
        with self.assertRaises(MerkleProofError):
            compute_consistency_proof(LEAF_INPUTS, 5, 2)
        with self.assertRaises(MerkleProofError):
            verify_consistency_proof(5, 2, [], ROOT_HASHES[5], ROOT_HASHES[2])

    def test_proof_beyond_the_available_entries_is_refused(self) -> None:
        with self.assertRaises(MerkleProofError):
            compute_consistency_proof(LEAF_INPUTS[:4], 2, 6)

    def test_equal_sizes_need_an_empty_proof(self) -> None:
        verify_consistency_proof(4, 4, [], ROOT_HASHES[4], ROOT_HASHES[4])
        with self.assertRaises(MerkleProofError):
            verify_consistency_proof(
                4, 4, [ROOT_HASHES[2]], ROOT_HASHES[4], ROOT_HASHES[4]
            )

    def test_nonempty_growth_needs_a_nonempty_proof(self) -> None:
        with self.assertRaises(MerkleProofError):
            verify_consistency_proof(2, 5, [], ROOT_HASHES[2], ROOT_HASHES[5])


class ArtifactRecordConsistencyTests(unittest.TestCase):
    """The property this module exists for, stated over real artifact records."""

    def setUp(self) -> None:
        self.history = chain_records(
            [
                {"decision_id": f"DE-20260804-{index:03d}", "summary": f"call {index}"}
                for index in range(1, 10)
            ]
        )

    def test_growth_verifies_without_rereading_the_earlier_records(self) -> None:
        checked_at = 4
        root1 = records_root(self.history[:checked_at])

        proof = records_consistency_proof(self.history, checked_at)

        # The verifier is handed the two roots and the proof — never the
        # records. That is the whole point: it cannot reread history.
        verify_consistency_proof(
            checked_at,
            len(self.history),
            proof,
            root1,
            records_root(self.history),
        )
        self.assertLess(len(proof), len(self.history))

    def test_editing_an_earlier_record_breaks_the_proof(self) -> None:
        checked_at = 4
        root1 = records_root(self.history[:checked_at])

        tampered = [dict(record) for record in self.history]
        tampered[1]["summary"] = "call 2 (rewritten)"
        # Relink so the linear append chain still passes: this is exactly the
        # rewrite `verify_append_chain` cannot detect on its own.
        tampered = chain_records(tampered)
        self.assertEqual([], verify_append_chain(tampered, "decisions.jsonl"))

        with self.assertRaises(MerkleProofError):
            verify_consistency_proof(
                checked_at,
                len(tampered),
                records_consistency_proof(tampered, checked_at),
                root1,
                records_root(tampered),
            )

    def test_dropping_an_earlier_record_breaks_the_proof(self) -> None:
        checked_at = 4
        root1 = records_root(self.history[:checked_at])
        shortened = chain_records(self.history[:2] + self.history[3:])

        with self.assertRaises(MerkleProofError):
            verify_consistency_proof(
                checked_at,
                len(shortened),
                records_consistency_proof(shortened, checked_at),
                root1,
                records_root(shortened),
            )

    def test_record_entry_commits_to_the_stored_chain_fields(self) -> None:
        record = dict(self.history[2])
        relinked = dict(record, prev_hash=None)
        self.assertNotEqual(record_entry(record), record_entry(relinked))


if __name__ == "__main__":
    unittest.main()
