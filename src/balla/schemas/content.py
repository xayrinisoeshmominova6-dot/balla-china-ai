"""Kontent holatlari va tasdiqlash qoidalari.

Har bir post quyidagi yo'ldan o'tadi:

    QORALAMA -> TEKSHIRUVDA -> TASDIQLANGAN -> JOYLANGAN
                     |
                     v
                RAD ETILGAN -> QORALAMA (qayta ishlash uchun)

Qoida kodning o'zida yozilgan: postni TASDIQLANGAN holatidan
boshqa holatdan JOYLANGAN holatiga o'tkazib bo'lmaydi.
"""

from __future__ import annotations

from enum import Enum


class ContentStatus(str, Enum):
    DRAFT = "draft"            # Qoralama — AI yaratdi
    IN_REVIEW = "in_review"    # Tekshiruvda — odam ko'rib chiqmoqda
    APPROVED = "approved"      # Tasdiqlangan — joylashga ruxsat bor
    REJECTED = "rejected"      # Rad etilgan
    PUBLISHED = "published"    # Instagram'ga joylangan


ALLOWED_TRANSITIONS: dict[ContentStatus, set[ContentStatus]] = {
    ContentStatus.DRAFT: {ContentStatus.IN_REVIEW},
    ContentStatus.IN_REVIEW: {ContentStatus.APPROVED, ContentStatus.REJECTED},
    ContentStatus.REJECTED: {ContentStatus.DRAFT},
    ContentStatus.APPROVED: {ContentStatus.PUBLISHED, ContentStatus.IN_REVIEW},
    ContentStatus.PUBLISHED: set(),
}


class InvalidTransitionError(ValueError):
    pass


def check_transition(current: ContentStatus, new: ContentStatus) -> None:
    if new not in ALLOWED_TRANSITIONS[current]:
        raise InvalidTransitionError(
            f"'{current.value}' holatidan '{new.value}' holatiga o'tib bo'lmaydi."
        )


class ContentType(str, Enum):
    LESSON = "lesson"
    CAROUSEL = "carousel"
    REEL = "reel"
    CALENDAR = "calendar"
