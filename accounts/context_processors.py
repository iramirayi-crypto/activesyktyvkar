from .models import Notification


def notifications_count(request):

    if request.user.is_authenticated:

        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()

        is_moderator = request.user.groups.filter(
            name="Модераторы"
        ).exists()

    else:
        unread_count = 0
        is_moderator = False

    return {
        "unread_notifications_count": unread_count,
        "is_moderator": is_moderator,
    }