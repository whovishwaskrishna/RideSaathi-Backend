from app.models.notification import Notification

async def create_notification(db, user_id, title, message):
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message
    )

    db.add(notification)
    db.commit()