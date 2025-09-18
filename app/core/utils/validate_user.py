from fastapi import HTTPException


def validate_user(user_id: int):
    """
    Check if user_id is valid.
    :param user_id: target user ID.
    :return: True if valid, false if not.
    """
    if user_id is None:
        raise HTTPException(status_code=404, detail="No user id provided!")
    return True
