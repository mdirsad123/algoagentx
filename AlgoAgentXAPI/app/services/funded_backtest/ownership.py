def can_access_funded_resource(*, owner_user_id, requesting_user_id, is_admin=False, is_template=False, write=False) -> bool:
    if is_admin:
        return True
    if str(owner_user_id or "") == str(requesting_user_id or ""):
        return True
    if not write and is_template:
        return True
    return False
