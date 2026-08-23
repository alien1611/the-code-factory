from app.profile import get_profile


def test_access_own_profile():
    """
    Verify that user 101 can successfully access profile 101.
    """

    profile = get_profile(
        101,
        101
    )

    assert profile is not None
