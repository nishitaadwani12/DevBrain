from app.services.chunking import chunk_segments
from app.services.parsing import Segment


def test_short_text_is_single_chunk():
    chunks = chunk_segments([Segment(text="a short sentence")], chunk_tokens=100)
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].token_count > 0


def test_long_text_splits_into_multiple_chunks():
    text = "word " * 2000
    chunks = chunk_segments([Segment(text=text)], chunk_tokens=100, overlap=10)
    assert len(chunks) > 1
    # indices are contiguous and start at 0
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_page_attribution_preserved_across_segments():
    segments = [
        Segment(text="page one content " * 100, page=1),
        Segment(text="page two content " * 100, page=2),
    ]
    chunks = chunk_segments(segments, chunk_tokens=50, overlap=5)
    pages = {c.page for c in chunks}
    assert pages == {1, 2}
    # every chunk carries a page from its source segment
    assert all(c.page in (1, 2) for c in chunks)


def test_empty_segments_yield_no_chunks():
    assert chunk_segments([]) == []
    assert chunk_segments([Segment(text="   ")]) == []
