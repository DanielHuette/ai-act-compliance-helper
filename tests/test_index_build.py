"""Incremental, resumable and language-aware building of the search index.

Context: a full CPU build takes an hour or more, so a rebuild must embed only units whose id or
index text changed, resume from checkpoints after an abort and never mix languages or models; a
counting fake embedder shows exactly what was embedded. | Input: a corpus sample, the fake
embedder, temporary index files | Output: pass when reuse, checkpoints, file names and language
checks behave correctly.
"""

from __future__ import annotations

import gzip
import json

import numpy as np
import pytest

from compliance_helper.domain import Unit
from compliance_helper.i18n import Language
from compliance_helper.search import store
from compliance_helper.search.embedding import EmbeddingResult, HashingEmbedder
from compliance_helper.search.index import SearchIndex
from compliance_helper.search.keywords import tokenize


class CountingEmbedder(HashingEmbedder):
    """Hashing embedder with sparse weights that records every passage it embeds."""

    def __init__(self, name: str = "counting-fake", fail_after: int | None = None) -> None:
        self.name = name
        self.embedded: list[str] = []
        self._fail_after = fail_after

    def embed_passages(self, texts: list[str]) -> EmbeddingResult:
        if self._fail_after is not None and len(self.embedded) + len(texts) > self._fail_after:
            raise RuntimeError("simulated abort")
        self.embedded.extend(texts)
        dense = self._encode(texts).dense
        weights = [dict.fromkeys(text.lower().split()[:5], 1.0) for text in texts]
        return EmbeddingResult(dense=dense, sparse_weights=weights)


@pytest.fixture(scope="module")
def sample(corpus) -> list[Unit]:
    return [unit for unit in corpus if unit.id.startswith(("AI-Act/art-5", "GDPR/art-22"))][:12]


def _built(units: list[Unit], embedder: CountingEmbedder, **options) -> SearchIndex:
    index = SearchIndex(units, embedder)
    index.build(batch_size=2, batches_per_checkpoint=1, **options)
    return index


def _edited(units: list[Unit]) -> list[Unit]:
    changed = units[3].model_copy(update={"text": units[3].text + " Geändert."})
    added = units[0].model_copy(update={"id": "AI-Act/art-5/para-99", "text": "Neue Einheit."})
    return [*units[:3], changed, *units[4:], added]


def test_rebuild_embeds_only_new_and_changed_units(sample, tmp_path):
    base = tmp_path / "search_index"
    _built(sample, CountingEmbedder()).save(base)
    edited = _edited(sample)

    embedder = CountingEmbedder()
    reusable = store.ReusableEmbeddings.from_index(
        base, embedder.name, embedder.dimensions, Language.DE
    )
    rebuilt = _built(edited, embedder, reusable=reusable)

    assert len(embedder.embedded) == 2
    fresh = _built(edited, CountingEmbedder())
    assert np.allclose(rebuilt.vectors, fresh.vectors)
    assert rebuilt.sparse_weights == fresh.sparse_weights
    assert rebuilt.text_hashes == fresh.text_hashes


def test_rebuilt_index_searches_like_a_fresh_one(sample, tmp_path):
    base = tmp_path / "search_index"
    _built(sample, CountingEmbedder()).save(base)
    edited = _edited(sample)
    reusable = store.ReusableEmbeddings.from_index(base, "counting-fake", 256, Language.DE)
    rebuilt = _built(edited, CountingEmbedder(), reusable=reusable)
    fresh = _built(edited, CountingEmbedder())
    question = "Emotionserkennung am Arbeitsplatz"
    assert [hit.unit.id for hit in rebuilt.search(question, count=5, rerank=False)] == [
        hit.unit.id for hit in fresh.search(question, count=5, rerank=False)
    ]


@pytest.mark.parametrize(
    "model,dimensions,language",
    [
        ("another-model", 256, Language.DE),
        ("counting-fake", 128, Language.DE),
        ("counting-fake", 256, Language.EN),
    ],
)
def test_nothing_is_reused_across_models_dimensions_or_languages(
    sample, tmp_path, model, dimensions, language
):
    base = tmp_path / "search_index"
    _built(sample, CountingEmbedder()).save(base)
    assert not store.ReusableEmbeddings.from_index(base, model, dimensions, language)


def test_index_without_text_hashes_offers_nothing(sample, tmp_path):
    """Without hashes a stored vector cannot be shown to belong to the current text."""
    base = tmp_path / "search_index"
    _built(sample, CountingEmbedder()).save(base)
    metadata_path = store.sibling(base, store.METADATA_SUFFIX)
    with gzip.open(metadata_path, "rt", encoding="utf-8") as file:
        metadata = json.load(file)
    del metadata["text_hashes"]
    with gzip.open(metadata_path, "wt", encoding="utf-8") as file:
        json.dump(metadata, file)
    assert not store.ReusableEmbeddings.from_index(base, "counting-fake", 256, Language.DE)


def test_missing_index_offers_nothing(tmp_path):
    assert not store.ReusableEmbeddings.from_index(
        tmp_path / "search_index", "counting-fake", 256, Language.DE
    )


def test_aborted_build_resumes_from_checkpoints(sample, tmp_path):
    checkpoints = tmp_path / "checkpoints"
    with pytest.raises(RuntimeError, match="simulated abort"):
        _built(sample, CountingEmbedder(fail_after=5), checkpoint_dir=checkpoints)

    resumed_embedder = CountingEmbedder()
    resumed = _built(sample, resumed_embedder, checkpoint_dir=checkpoints)

    assert len(resumed_embedder.embedded) == len(sample) - 4
    fresh = _built(sample, CountingEmbedder())
    assert np.allclose(resumed.vectors, fresh.vectors)
    assert resumed.sparse_weights == fresh.sparse_weights


def test_checkpoint_of_changed_text_is_not_reused(sample, tmp_path):
    """A checkpoint is named after its texts, so an edited unit is embedded again."""
    checkpoints = tmp_path / "checkpoints"
    _built(sample, CountingEmbedder(), checkpoint_dir=checkpoints)
    changed = [sample[0].model_copy(update={"text": "Anderer Wortlaut."}), *sample[1:]]

    embedder = CountingEmbedder()
    rebuilt = _built(changed, embedder, checkpoint_dir=checkpoints)

    assert len(embedder.embedded) == 2
    assert np.allclose(rebuilt.vectors, _built(changed, CountingEmbedder()).vectors)


def test_index_files_carry_the_language_infix(tmp_path):
    german, english = (
        store.index_path(Language.DE, tmp_path),
        store.index_path(Language.EN, tmp_path),
    )
    assert german.name == "search_index"
    assert english.name == "search_index.en"
    assert [path.name for path in store.index_files(english)] == [
        "search_index.en.vectors.npy",
        "search_index.en.meta.json.gz",
        "search_index.en.meta.json",
    ]


def test_saved_index_records_its_language(sample, tmp_path):
    base = store.index_path(Language.EN, tmp_path)
    index = SearchIndex(sample, CountingEmbedder(), Language.EN)
    index.build()
    index.save(base)
    summary = json.loads(store.sibling(base, store.SUMMARY_SUFFIX).read_text(encoding="utf-8"))
    assert summary["language"] == "en"
    loaded = SearchIndex.load(Language.EN, sample, CountingEmbedder(), path=base)
    assert loaded.language is Language.EN
    assert loaded.keywords.language is Language.EN


def test_index_of_another_language_is_rejected(sample, tmp_path):
    base = tmp_path / "search_index"
    index = SearchIndex(sample, CountingEmbedder(), Language.EN)
    index.build()
    index.save(base)
    with pytest.raises(RuntimeError, match="language en"):
        SearchIndex.load(Language.DE, sample, CountingEmbedder(), path=base)


def test_missing_english_index_names_the_build_command(sample, tmp_path):
    from compliance_helper.i18n import use_language

    with use_language(Language.EN), pytest.raises(FileNotFoundError) as error:
        SearchIndex.load(Language.EN, sample, CountingEmbedder(), path=tmp_path / "missing")
    assert "(English)" in str(error.value)
    assert "--language en" in str(error.value)


def test_index_text_is_rendered_in_the_index_language(sample):
    article = next(unit for unit in sample if unit.id.startswith("AI-Act/art-5/para-1"))
    german = SearchIndex([article], CountingEmbedder(), Language.DE).index_texts()[0]
    english = SearchIndex([article], CountingEmbedder(), Language.EN).index_texts()[0]
    assert german.startswith("Artikel 5 Absatz 1")
    assert english.startswith("Article 5(1)")


def test_english_tokenization_drops_stopwords_and_plurals():
    assert tokenize("The processing of employees' data", Language.EN) == [
        "processing",
        "employee",
        "data",
    ]
    assert tokenize("Categories of high-risk systems", Language.EN) == [
        "category",
        "high",
        "risk",
        "system",
        "high",
        "risk",
    ]


def test_german_tokenization_drops_folded_stopwords():
    """Stopwords are folded like the text, so "für" and "über" are removed as well."""
    assert tokenize("Pflichten für Betreiber über Hochrisiko-KI", Language.DE) == [
        "pflichten",
        "betreiber",
        "hochrisiko",
        "ki",
        "hochrisiko",
    ]
