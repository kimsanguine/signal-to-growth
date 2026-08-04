"""RFC 6962 Merkle tree hashing and consistency proofs over append-only records.

`append_only.verify_append_chain` answers "is this whole file internally
consistent?" and answers it by rehashing every line. That is the right check
when you hold the file. It is the wrong check when you hold only a *memory* of
the file: an agent that verified `decisions.jsonl` at 40 records and comes back
to find 900 has no way, short of rereading all 900, to establish that the
original 40 are untouched.

A Merkle tree gives that second check. Commit to the log as a single root hash
over its entries; then a *consistency proof* — O(log n) sibling hashes — lets a
verifier holding only `(size1, root1)` confirm that a tree of `size2 > size1`
still contains the first `size1` entries unchanged and in order. The verifier
never sees the entries. This is the standard Certificate Transparency
construction from RFC 6962 §2.1.2 [1], ported here from the algorithms in
`transparency-dev/merkle` (Apache-2.0) [2] rather than copied: no Go code is
vendored, and the test vectors that pin us to the standard carry their
attribution in `tests/test_merkle.py`.

Honest about the cost split: *verification* is O(log n) hashes and reads no
records, which is the property worth having. *Proof generation* here is O(n) —
it rebuilds the tree from the entries — because the prover is the party that
already holds the log. Making generation incremental would need a persisted
compact range, which nothing in this repository asks for yet.

Also honest about the threat model, which is unchanged from `append_only`: the
hashes use no secret, so whoever can rewrite the artifact can also recompute a
matching root. What a root pins down is a claim someone else recorded earlier.
It is tamper *evidence* against an edit that did not also rewrite every
previously published root, not tamper proofing.

This module is additive. It replaces no part of the existing append chain, and
nothing in the router or CLI depends on it.

[1] https://datatracker.ietf.org/doc/html/rfc6962#section-2.1
[2] https://github.com/transparency-dev/merkle
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Sequence


# RFC 6962 §2.1 domain separation: leaves and internal nodes are hashed with
# different prefixes so that no internal node hash can be replayed as a leaf.
LEAF_PREFIX = b"\x00"
NODE_PREFIX = b"\x01"


class MerkleProofError(ValueError):
    """Raised when a consistency proof is malformed or does not verify."""


def empty_root() -> bytes:
    """Return the root of a tree with no entries (RFC 6962: SHA-256 of nothing)."""
    return hashlib.sha256(b"").digest()


def hash_leaf(entry: bytes) -> bytes:
    """Return the leaf hash of one entry."""
    return hashlib.sha256(LEAF_PREFIX + entry).digest()


def hash_children(left: bytes, right: bytes) -> bytes:
    """Return the hash of an internal node with the two given children."""
    return hashlib.sha256(NODE_PREFIX + left + right).digest()


def _down_to_power_of_two(size: int) -> int:
    """Return the largest power of two strictly smaller than `size` (size >= 2)."""
    if size < 2:
        raise ValueError("_down_to_power_of_two requires size >= 2")
    return 1 << ((size - 1).bit_length() - 1)


def _trailing_zeros(value: int) -> int:
    """Return the number of trailing zero bits of a positive integer."""
    return (value & -value).bit_length() - 1


def root_from_entries(entries: Sequence[bytes]) -> bytes:
    """Return the Merkle tree hash of `entries`, per RFC 6962 §2.1.

    The split point is the largest power of two below the entry count, which is
    what makes the tree append-only friendly: adding entries never reshapes the
    left subtrees that earlier roots committed to.
    """
    if not entries:
        return empty_root()
    if len(entries) == 1:
        return hash_leaf(entries[0])
    split = _down_to_power_of_two(len(entries))
    return hash_children(
        root_from_entries(entries[:split]),
        root_from_entries(entries[split:]),
    )


def compute_consistency_proof(
    entries: Sequence[bytes],
    size1: int,
    size2: int,
) -> list[bytes]:
    """Return the consistency proof between tree sizes `size1` and `size2`.

    Requires `0 < size1 <= size2 <= len(entries)`. The returned hashes let a
    verifier holding only `(size1, root1)` recompute the size-`size2` root, and
    so accept the larger tree only if it really extends the smaller one.
    """
    if size1 <= 0:
        raise MerkleProofError(
            "a consistency proof from an empty tree proves nothing — size1 must "
            "be at least 1"
        )
    if size1 > size2:
        raise MerkleProofError(f"size1 ({size1}) is larger than size2 ({size2})")
    if size2 > len(entries):
        raise MerkleProofError(
            f"size2 ({size2}) exceeds the {len(entries)} entries provided"
        )
    return _consistency_proof(entries[:size2], size2, size1, have_root1=True)


def _consistency_proof(
    entries: Sequence[bytes],
    size2: int,
    size1: int,
    have_root1: bool,
) -> list[bytes]:
    """Recursive RFC 6962 §2.1.3 consistency proof over `entries[:size2]`.

    `have_root1` records whether the caller already knows the root of the
    size-`size1` subtree. When it does, that root is omitted from the proof: the
    verifier supplies it. It is only unknown once the recursion has descended
    into a right subtree, where the size-`size1` boundary no longer coincides
    with a subtree the verifier holds.
    """
    if size1 == size2:
        if have_root1:
            return []
        return [root_from_entries(entries[:size1])]

    split = _down_to_power_of_two(size2)
    if size1 <= split:
        # The size1 root lives in the left subtree. Recurse there, then record
        # the right subtree, which exists only in the larger tree.
        return _consistency_proof(entries[:split], split, size1, have_root1) + [
            root_from_entries(entries[split:size2])
        ]
    # The size1 root sits at the same level as the size2 root. Recurse into the
    # right subtree, and record the left subtree, which both trees share.
    return _consistency_proof(
        entries[split:size2], size2 - split, size1 - split, have_root1=False
    ) + [root_from_entries(entries[:split])]


def _chain_inner(seed: bytes, proof: Sequence[bytes], index: int) -> bytes:
    """Fold `proof` into `seed`, taking each node's side from a bit of `index`."""
    for level, sibling in enumerate(proof):
        if (index >> level) & 1 == 0:
            seed = hash_children(seed, sibling)
        else:
            seed = hash_children(sibling, seed)
    return seed


def _chain_inner_right(seed: bytes, proof: Sequence[bytes], index: int) -> bytes:
    """Fold only the left-hand siblings of `proof` into `seed`.

    Skipping the right-hand siblings is what turns the path into the *earlier*
    version of the same subtree: those right siblings are the entries that were
    appended after the smaller tree was published.
    """
    for level, sibling in enumerate(proof):
        if (index >> level) & 1 == 1:
            seed = hash_children(sibling, seed)
    return seed


def _chain_border_right(seed: bytes, proof: Sequence[bytes]) -> bytes:
    """Fold `proof` into `seed` along the tree's right border (all left siblings)."""
    for sibling in proof:
        seed = hash_children(sibling, seed)
    return seed


def root_from_consistency_proof(
    size1: int,
    size2: int,
    proof: Sequence[bytes],
    root1: bytes,
) -> bytes:
    """Return the size-`size2` root implied by `proof` and the size-`size1` root.

    Reads no entries: the proof plus `root1` is the whole input. Raises
    `MerkleProofError` if the proof is the wrong length for the two sizes, or if
    its own nodes fail to rebuild `root1`.
    """
    if size2 < size1:
        raise MerkleProofError(f"size2 ({size2}) is smaller than size1 ({size1})")
    if size1 <= 0:
        raise MerkleProofError(
            "a consistency proof from an empty tree proves nothing — size1 must "
            "be at least 1"
        )
    if size1 == size2:
        if proof:
            raise MerkleProofError(
                "size1 equals size2, so the proof must be empty, but it carries "
                f"{len(proof)} node(s)"
            )
        return root1
    if not proof:
        raise MerkleProofError(
            f"a proof between sizes {size1} and {size2} cannot be empty"
        )

    # Level at which the path to entry size1-1 diverges from the path to the
    # last entry of the larger tree, and how many left siblings sit above it.
    fork_level = ((size1 - 1) ^ (size2 - 1)).bit_length()
    border = ((size1 - 1) >> fork_level).bit_count()
    # Height of the rightmost perfect subtree of the smaller tree: the proof
    # starts at this level, because everything below it is already summarized.
    shift = _trailing_zeros(size1)
    inner = fork_level - shift

    if size1 == 1 << shift:
        # The smaller tree is perfect, so its own root is that rightmost
        # subtree's root. The verifier already holds it, so it is not sent.
        seed, offset = root1, 0
    else:
        seed, offset = proof[0], 1

    expected = offset + inner + border
    if len(proof) != expected:
        raise MerkleProofError(
            f"proof has {len(proof)} node(s) but a proof between sizes {size1} "
            f"and {size2} must have {expected}"
        )
    rest = proof[offset:]
    index = (size1 - 1) >> shift

    if offset == 1:
        # The proof carries nodes that lie inside the smaller tree. Rebuild
        # root1 from them first, so a proof that verifies against root2 by
        # smuggling in a rewritten history is rejected here.
        height = (size1 - 1).bit_length()
        sub_inner = min(height, fork_level) - shift
        rebuilt = _chain_inner_right(seed, rest[:sub_inner], index)
        rebuilt = _chain_border_right(rebuilt, rest[inner:])
        if rebuilt != root1:
            raise MerkleProofError(
                "the proof does not rebuild the size1 root — the recorded "
                "history does not match the proof"
            )

    root2 = _chain_inner(seed, rest[:inner], index)
    return _chain_border_right(root2, rest[inner:])


def verify_consistency_proof(
    size1: int,
    size2: int,
    proof: Sequence[bytes],
    root1: bytes,
    root2: bytes,
) -> None:
    """Raise `MerkleProofError` unless `proof` proves size2 extends size1.

    Returns None on success rather than a boolean, so a caller cannot mistake an
    ignored return value for a passing check.
    """
    computed = root_from_consistency_proof(size1, size2, proof, root1)
    if computed != root2:
        raise MerkleProofError(
            "the proof rebuilds a different size2 root — the larger log does not "
            "extend the log that was verified earlier"
        )


def record_entry(record: dict[str, Any]) -> bytes:
    """Return the canonical bytes committed to for one append-only record.

    The whole stored record is hashed, `prev_hash` and `record_hash` included,
    so a leaf pins the exact line as written rather than a projection of it.
    Serialization matches `append_only.compute_record_hash`: sorted keys, no
    incidental whitespace, so two readers of the same line agree on the leaf.
    """
    return json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def records_root(records: Sequence[dict[str, Any]]) -> bytes:
    """Return the Merkle root over append-only artifact records."""
    return root_from_entries([record_entry(record) for record in records])


def records_consistency_proof(
    records: Sequence[dict[str, Any]],
    size1: int,
    size2: int | None = None,
) -> list[bytes]:
    """Return the consistency proof between two sizes of an artifact's history.

    `size2` defaults to the current record count, which is the usual question:
    "does the log I have now still contain the log I checked at size1?"
    """
    entries = [record_entry(record) for record in records]
    return compute_consistency_proof(
        entries, size1, len(entries) if size2 is None else size2
    )
