"""Load the curated CEFR English path into a studio template track."""

import json
from pathlib import Path

from scheduling.models import CurriculumTrack
from scheduling.services.curriculum import create_track, update_track

CEFR_ENGLISH_PATH = Path(__file__).resolve().parent.parent / 'data' / 'cefr_english_path.json'


def load_cefr_english_data():
    with CEFR_ENGLISH_PATH.open(encoding='utf-8') as handle:
        return json.load(handle)


def _module_rows(data):
    return [
        {**row, 'sort_order': index}
        for index, row in enumerate(data['modules'])
    ]


def seed_cefr_english_track(*, created_by=None, refresh=False):
    """Create the CEFR template once. Returns (track, created).

    Refreshing rewrites the modules, which resets every enrolled student's progress
    on this track — so it only happens when asked for explicitly.
    """
    data = load_cefr_english_data()
    existing = CurriculumTrack.objects.filter(
        title=data['title'],
        framework=CurriculumTrack.FRAMEWORK_CEFR,
    ).first()

    if existing is not None:
        if refresh:
            existing, _ = update_track(
                existing,
                description=data['description'],
                subject=data['subject'],
                modules=_module_rows(data),
            )
        return existing, False

    track, _ = create_track(
        title=data['title'],
        description=data['description'],
        is_template=True,
        created_by=created_by,
        modules=_module_rows(data),
        framework=CurriculumTrack.FRAMEWORK_CEFR,
        subject=data['subject'],
    )
    return track, True
