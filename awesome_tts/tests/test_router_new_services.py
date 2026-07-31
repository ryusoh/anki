# -*- coding: utf-8 -*-
"""Tests that the new free services are pinned and highlighted."""

from awesome_tts import awesometts
from awesome_tts.awesometts.router import NEW_SERVICE_ORDER


def test_new_services_pinned_to_top():
    """The three new services must appear first, in the configured order."""
    services = awesometts.router.get_services()
    svc_ids = [svc_id for svc_id, _ in services]

    # Collect only the pinned services that are actually available.
    pinned_in_list = [svc_id for svc_id in svc_ids if svc_id in NEW_SERVICE_ORDER]
    assert pinned_in_list == [svc_id for svc_id in NEW_SERVICE_ORDER if svc_id in svc_ids]

    # If all three are available, they occupy the first three slots.
    if all(svc_id in svc_ids for svc_id in NEW_SERVICE_ORDER):
        assert svc_ids[:3] == NEW_SERVICE_ORDER


def test_new_services_have_star_marker():
    """New-service display names must carry the star marker."""
    services = awesometts.router.get_services()
    names_by_id = dict(services)

    for svc_id in NEW_SERVICE_ORDER:
        if svc_id in names_by_id:
            assert names_by_id[svc_id].startswith('★'), f"{svc_id} is not visually marked"


def test_remaining_services_are_alphabetical():
    """After the pinned block, the rest of the list stays alphabetical."""
    services = awesometts.router.get_services()
    rest = [name.lower() for svc_id, name in services if svc_id not in NEW_SERVICE_ORDER]
    assert rest == sorted(rest)
