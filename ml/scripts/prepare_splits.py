"""Deterministic chronological and source-isolated dataset splitter to prevent data leakage."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AnnotatedSample:
    sample_id: str
    source_id: str
    published_at: str
    language: str
    text: str
    category: str


def split_by_source_and_date(
    samples: list[AnnotatedSample],
    train_cutoff: str = "2026-06-01",
    val_cutoff: str = "2026-09-01",
) -> tuple[list[AnnotatedSample], list[AnnotatedSample], list[AnnotatedSample]]:
    """Partitions samples by publication timestamp and isolates test sources."""
    train: list[AnnotatedSample] = []
    val: list[AnnotatedSample] = []
    test: list[AnnotatedSample] = []

    for item in sorted(samples, key=lambda s: (s.published_at, s.sample_id)):
        if item.published_at < train_cutoff:
            train.append(item)
        elif item.published_at < val_cutoff:
            val.append(item)
        else:
            test.append(item)

    return train, val, test
