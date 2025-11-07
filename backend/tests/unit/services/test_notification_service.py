import pytest
from sqlalchemy.orm import Session

import app.services.notifications as notif_service
from app.models.notification import Notification
from tests.factories import UserFactory, RoleFactory

def _user(role="user"):
    return UserFactory(role=RoleFactory(name=role))

def test_notify_creates_notification(db_session: Session):
    recipient = _user()
    actor = _user()
    n = notif_service.notify(
        db_session,
        recipient_id=recipient.id,
        action="liked",
        actor_id=actor.id,
        target_type="story",
        target_id=None,
    )
    assert isinstance(n, Notification)
    assert n.recipient_id == recipient.id
    assert n.actor_id == actor.id
    assert n.action == "liked"
    assert n.is_read is False

def test_list_my_notifications_all_vs_unread_and_ordering(db_session: Session):
    u = _user()
    a = _user()
    # create 3 notifs
    n1 = notif_service.notify(db_session, u.id, "a", actor_id=a.id)
    n2 = notif_service.notify(db_session, u.id, "b", actor_id=a.id)
    n3 = notif_service.notify(db_session, u.id, "c", actor_id=a.id)
    # mark one as read
    notif_service.mark_as_read(db_session, n2.id, u.id)

    total_all, items_all = notif_service.list_my_notifications(db_session, u.id, limit=50, offset=0, unread_only=False)
    assert total_all == 3
    # ordered desc by created_at: last created first
    assert [i.id for i in items_all] == [n3.id, n2.id, n1.id]

    total_unread, items_unread = notif_service.list_my_notifications(db_session, u.id, limit=50, offset=0, unread_only=True)
    assert total_unread == 2
    assert {i.id for i in items_unread} == {n3.id, n1.id}

def test_list_my_notifications_pagination(db_session: Session):
    u = _user(); a = _user()
    ids = []
    for i in range(5):
        ids.append(notif_service.notify(db_session, u.id, f"act{i}", actor_id=a.id).id)

    # page size 2, first page should return newest two
    total, page1 = notif_service.list_my_notifications(db_session, u.id, limit=2, offset=0)
    assert total == 5
    assert [n.id for n in page1] == ids[-1:-3:-1]  # newest two

    # second page
    _, page2 = notif_service.list_my_notifications(db_session, u.id, limit=2, offset=2)
    assert [n.id for n in page2] == ids[-3:-5:-1]

def test_mark_as_read_happy_path_and_idempotent(db_session: Session):
    u = _user(); a = _user()
    n = notif_service.notify(db_session, u.id, "ping", actor_id=a.id)
    out1 = notif_service.mark_as_read(db_session, n.id, u.id)
    assert out1 and out1.is_read is True

    # idempotent: calling again returns same object (already read)
    out2 = notif_service.mark_as_read(db_session, n.id, u.id)
    assert out2 and out2.is_read is True

def test_mark_as_read_wrong_user_returns_none(db_session: Session):
    r1 = _user(); r2 = _user(); a = _user()
    n = notif_service.notify(db_session, r1.id, "like", actor_id=a.id)
    out = notif_service.mark_as_read(db_session, n.id, r2.id)
    assert out is None
    # original remains unread
    reloaded = db_session.get(Notification, n.id)
    assert reloaded.is_read is False

def test_mark_all_as_read_only_affects_caller(db_session: Session):
    u1 = _user(); u2 = _user(); a = _user()
    # u1 -> 3 unread; u2 -> 1 unread
    for _ in range(3):
        notif_service.notify(db_session, u1.id, "x", actor_id=a.id)
    n_u2 = notif_service.notify(db_session, u2.id, "y", actor_id=a.id)

    count = notif_service.mark_all_as_read(db_session, u1.id)
    assert count == 3

    # u1 all read
    _, items_u1 = notif_service.list_my_notifications(db_session, u1.id, limit=10, offset=0, unread_only=True)
    assert items_u1 == []

    # u2 unaffected
    re_u2 = db_session.get(Notification, n_u2.id)
    assert re_u2.is_read is False
