def to_response_dict(res_type, obj) -> dict:
    """
    Convert response to dict.
    :param res_type: response type
    :param obj: Response to convert.
    :return: Response dict.
    """
    return res_type.model_validate(obj, from_attributes=True).model_dump()
