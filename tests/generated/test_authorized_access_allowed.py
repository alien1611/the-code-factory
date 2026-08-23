from app.profile import get_profile


def test_authorized_access_allowed():
    """
    Verify that user 101 can access their own profile.
    """

    profile = get_profile(
        101,
        101
    )

    assert profile is not None
