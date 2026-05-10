from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user_profile import UserPublicProfileResponse


def build_user_public_profile(
    user: User | None,
) -> UserPublicProfileResponse | None:
    if user is None:
        return None
    return UserPublicProfileResponse.model_validate(user)


def list_user_public_profiles_by_id(
    db: Session,
    user_ids: list[str],
) -> dict[str, UserPublicProfileResponse]:
    normalized_ids = [user_id.strip() for user_id in user_ids if user_id.strip()]
    if not normalized_ids:
        return {}
    users = UserRepository.list_by_ids(db, list(dict.fromkeys(normalized_ids)))
    return {user.id: UserPublicProfileResponse.model_validate(user) for user in users}
