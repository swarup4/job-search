"""Properties of the checks every no-fabrication guard stands on.

Example tests pin the cases someone thought of; these generate the ones nobody did.
If `verified_span` can be made to accept a span the source does not contain, every
"quote copied verbatim" rule in the pipeline is decorative.
"""

from __future__ import annotations

import re

from hypothesis import given, settings
from hypothesis import strategies as st

from agents.evidence import flatten, occurrences, slug, verified_span
from config.llm import as_document

text = st.text(
    alphabet=st.characters(codec="utf-8", exclude_categories=("Cs",)), min_size=0, max_size=400
)
words = st.lists(st.from_regex(r"[A-Za-z][A-Za-z0-9]{1,9}", fullmatch=True), min_size=1, max_size=6)


@given(text)
def test_flatten_is_idempotent(value: str) -> None:
    assert flatten(flatten(value)) == flatten(value)


@given(text, text)
def test_an_accepted_span_is_always_in_the_source(span: str, source: str) -> None:
    accepted = verified_span(span, flatten(source))
    if accepted is not None:
        assert flatten(accepted) in flatten(source)


@given(st.data(), st.text(min_size=20, max_size=400))
def test_any_long_enough_slice_of_the_source_is_accepted(data: st.DataObject, source: str) -> None:
    start = data.draw(st.integers(0, len(source) - 1))
    end = data.draw(st.integers(start, len(source)))
    span = source[start:end]
    # Line breaks and runs of spaces may differ between a quote and its source.
    if len(re.sub(r"\s+", " ", span).strip()) >= 8:
        assert verified_span(span.replace(" ", "\n"), flatten(source)) is not None


@given(st.text(alphabet="abcdefgh ", min_size=0, max_size=200), st.text(alphabet="xyz", min_size=8))
def test_a_span_sharing_no_characters_with_the_source_is_refused(source: str, span: str) -> None:
    assert verified_span(span, flatten(source)) is None


@given(words, text, text)
def test_a_label_placed_as_whole_words_is_counted(
    label_words: list[str], before: str, after: str
) -> None:
    label = " ".join(label_words)
    haystack = flatten(f"{before} {label} {after}")
    assert occurrences(label, haystack) >= 1


@given(text)
def test_slugging_is_stable(value: str) -> None:
    assert slug(slug(value)) == slug(value)


@settings(max_examples=300)
@given(text)
def test_no_text_can_close_its_own_fence(value: str) -> None:
    fenced = as_document("job_description", value)
    assert len(re.findall(r"<\s*/\s*document", fenced, re.IGNORECASE)) == 1
    assert fenced.endswith("</document>")
