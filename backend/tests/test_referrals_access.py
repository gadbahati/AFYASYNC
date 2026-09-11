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
