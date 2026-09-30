"""Point existing classes and sessions at curriculum tracks.

One track per subject · level · focus. The seeded CEFR path is left alone:
its title is not a catalog focus title, so this never folds catalog topics into it.
"""


def track_title(subject, level, focus):
    return f'{subject} · {level} · {focus}'[:200]


def link_catalog_to_tracks(apps):
    """Backfill ClassOffering.track and Session/ClassRequest.curriculum_module.

    `apps` is a Django app registry (migration state or django.apps.apps).
    Safe to run more than once.
    """
    CatalogFocus = apps.get_model('scheduling', 'CatalogFocus')
    ClassOffering = apps.get_model('scheduling', 'ClassOffering')
    ClassTopic = apps.get_model('scheduling', 'ClassTopic')
    ClassRequest = apps.get_model('scheduling', 'ClassRequest')
    Session = apps.get_model('scheduling', 'Session')
    CurriculumTrack = apps.get_model('scheduling', 'CurriculumTrack')
    CurriculumModule = apps.get_model('scheduling', 'CurriculumModule')

    tracks_by_key = {}
    for focus in CatalogFocus.objects.select_related('level__subject').all():
        subject = focus.level.subject.name
        level = focus.level.name
        topics = [(topic.title, topic.sort_order) for topic in focus.topics.all()]
        track = _ensure_track(CurriculumTrack, CurriculumModule, subject, level, focus.name, topics)
        tracks_by_key[(subject, level, focus.name)] = track

    for offering in ClassOffering.objects.all():
        key = (offering.subject, offering.level, offering.focus)
        topics = [
            (topic.title, topic.sort_order)
            for topic in ClassTopic.objects.filter(class_offering=offering)
        ]
        track = tracks_by_key.get(key)
        if track is None:
            track = _ensure_track(CurriculumTrack, CurriculumModule, *key, topics)
            tracks_by_key[key] = track
        else:
            _ensure_modules(CurriculumModule, track, topics)
        if offering.track_id != track.id:
            offering.track_id = track.id
            offering.save(update_fields=['track'])

    _link_lessons(Session, CurriculumModule, 'class_topic')
    _link_lessons(ClassRequest, CurriculumModule, 'class_topic')


def _ensure_track(CurriculumTrack, CurriculumModule, subject, level, focus, topics):
    title = track_title(subject, level, focus)
    track = CurriculumTrack.objects.filter(title=title).first()
    if track is None:
        track = CurriculumTrack.objects.create(
            title=title,
            description='',
            framework='custom',
            subject=(subject or '')[:100],
            cefr_band='',
            is_template=True,
            is_active=True,
        )
    _ensure_modules(CurriculumModule, track, topics)
    return track


def _ensure_modules(CurriculumModule, track, topics):
    existing = {
        module.title.casefold(): module
        for module in CurriculumModule.objects.filter(track=track)
    }
    for title, sort_order in topics:
        title = (title or '').strip()
        if not title or title.casefold() in existing:
            continue
        module = CurriculumModule.objects.create(
            track=track,
            title=title[:200],
            content='',
            sort_order=sort_order or 0,
            cefr_level='',
            skill_keys=[],
        )
        existing[title.casefold()] = module


def _link_lessons(model, CurriculumModule, topic_attr):
    topic_id_attr = f'{topic_attr}_id'
    rows = model.objects.filter(**{f'{topic_id_attr}__isnull': False, 'curriculum_module__isnull': True})
    for row in rows.select_related(topic_attr, 'class_offering'):
        offering = row.class_offering
        if offering is None or not offering.track_id:
            continue
        topic = getattr(row, topic_attr)
        module = None
        wanted = (topic.title or '').casefold()
        for candidate in CurriculumModule.objects.filter(track_id=offering.track_id):
            if candidate.title.casefold() == wanted:
                module = candidate
                break
        if module is None:
            continue
        row.curriculum_module_id = module.id
        row.save(update_fields=['curriculum_module'])
