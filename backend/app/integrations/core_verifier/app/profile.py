users = {
    101: {"name": "User A"},
    102: {"name": "User B"}
}


def get_profile(requesting_user_id, requested_user_id):
    if requesting_user_id != requested_user_id:
        raise PermissionError("Unauthorized access")

    return users[requested_user_id]