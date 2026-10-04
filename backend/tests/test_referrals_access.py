from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.referrals.service import ReferralError, get_referral_for_facility, get_transfer_for_facility


def test_get_referral_rejects_unrelated_facility() -> None:
    db = MagicMock()
    referral = SimpleNamespace(
        id=uuid4(),
        source_facility_id=uuid4(),
        destination_facility_id=uuid4(),
    )
    db.get.return_value = referral

    with pytest.raises(ReferralError, match="FACILITY_ACCESS_DENIED"):
        get_referral_for_facility(db, referral.id, uuid4())


def test_get_transfer_allows_destination_facility() -> None:
    db = MagicMock()
    dest = uuid4()
    transfer = SimpleNamespace(
        id=uuid4(),
        source_facility_id=uuid4(),
        destination_facility_id=dest,
    )
    db.get.return_value = transfer

    result = get_transfer_for_facility(db, transfer.id, dest)
    assert result is transfer


def test_build_referral_hie_package_rejects_destination_node_for_wrong_facility() -> None:
    from app.referrals.service import build_referral_hie_package, ReferralError

    db = MagicMock()
    referral_id = uuid4()
    source = uuid4()
    destination = uuid4()
    node = SimpleNamespace(id=uuid4(), status="ACTIVE", facility_id=uuid4())
    referral = SimpleNamespace(
        id=referral_id,
        source_facility_id=source,
        destination_facility_id=destination,
        status="ACCEPTED",
    )
    db.get.side_effect = lambda model, key: referral if key == referral_id else node

    with pytest.raises(ReferralError, match="HIE_DESTINATION_MISMATCH"):
        build_referral_hie_package(
            db,
            referral_id=referral_id,
            facility_id=source,
            destination_node_id=node.id,
        )
