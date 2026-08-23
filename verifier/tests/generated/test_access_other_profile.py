from app.profile import get_profile


def test_access_other_profile():
    """
    Verify that user 101 cannot access profile 102 and receives a PermissionError.
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
