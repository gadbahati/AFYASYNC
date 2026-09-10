from app.referrals.service import REFERRAL_TRANSITIONS, TRANSFER_TRANSITIONS


def test_referral_lifecycle_transitions_are_one_way():
    assert REFERRAL_TRANSITIONS["CREATED"] == {"SENT", "CANCELLED"}
    assert REFERRAL_TRANSITIONS["SENT"] == {"ACCEPTED", "DECLINED", "CANCELLED"}
    assert REFERRAL_TRANSITIONS["ACCEPTED"] == {"IN_PROGRESS", "CANCELLED"}
    assert REFERRAL_TRANSITIONS["IN_PROGRESS"] == {"COMPLETED", "CANCELLED"}
    assert REFERRAL_TRANSITIONS["COMPLETED"] == set()


def test_transfer_lifecycle_requires_ordered_states():
    assert TRANSFER_TRANSITIONS["REQUESTED"] == {"ACCEPTED", "CANCELLED"}
    assert TRANSFER_TRANSITIONS["ACCEPTED"] == {"IN_TRANSIT", "CANCELLED"}
    assert TRANSFER_TRANSITIONS["IN_TRANSIT"] == {"ARRIVED", "CANCELLED"}
    assert TRANSFER_TRANSITIONS["ARRIVED"] == set()
