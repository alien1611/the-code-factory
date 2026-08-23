from app.profile import get_profile


def test_unauthorized_access_denied():
    """
    Verify that user 101 cannot access the profile of user 102.
    """

    try:
        get_profile(
            101,
            102
        )

    except PermissionError:
        return

    raise AssertionError(
        "Expected unauthorized access to be rejected, "
        "but the profile was returned."
    )
