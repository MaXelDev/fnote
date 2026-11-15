from fnote.model import colors as c


def test_normalize():
    assert c.normalize("ABC") == "#aabbccff"
    assert c.normalize("#1F5FD1") == "#1f5fd1ff"
    assert c.normalize("#1f5fd180") == "#1f5fd180"
    assert c.normalize("#1f5fd1", alpha=0x8c) == "#1f5fd18c"
    assert c.normalize("rouge") is None and c.normalize("#12345") is None and c.normalize(None) is None


def test_recents_no_duplicates_and_capped():
    r = []
    for col in ["#111111", "#222222", "#111111ff", "#333333"]:
        r = c.push_recent(r, col)
    assert r == ["#333333ff", "#111111ff", "#222222ff"]
    for i in range(20):
        r = c.push_recent(r, f"#{i:06x}")
    assert len(r) == c.MAX_RECENT


def test_palettes():
    assert len(c.INK_PALETTE) >= 16 and len(c.HIGHLIGHTER_PALETTE) == 5
    assert all(c.normalize(x) for x in c.INK_PALETTE + c.HIGHLIGHTER_PALETTE)
