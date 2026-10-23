"""Would a negative keyword stop a positive keyword's own search? Used before adding negatives.

Google's rules for negatives (no close variants, plurals or synonyms):
  BROAD  [a b]  blocks a search containing every word, in any order
  PHRASE "a b"  blocks a search containing the words together, in that order
  EXACT  [a b]  blocks only the search "a b" itself

A negative "blocks" a positive keyword when the keyword's own text, searched as written, would be blocked.

    from negative_match import blocked
    blocked([("funeral singers", "EXACT")], [("london funeral singers", "PHRASE")])   # → []
"""


def words(text):
    return text.lower().split()


def blocks(neg_text, neg_match, kw_text):
    n, k = words(neg_text), words(kw_text)
    if neg_match == "EXACT":
        return n == k
    if neg_match == "PHRASE":
        return any(k[i:i + len(n)] == n for i in range(len(k) - len(n) + 1))
    if neg_match == "BROAD":
        return set(n) <= set(k)
    raise ValueError(f"unknown match type {neg_match!r}")


def blocked(negatives, positives):
    """Every (negative text, negative match, keyword text, keyword match) where the negative blocks the keyword."""
    return [(nt, nm, kt, km) for nt, nm in negatives for kt, km in positives if blocks(nt, nm, kt)]
