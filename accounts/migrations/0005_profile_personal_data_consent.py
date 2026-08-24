from django.db import migrations, models


def create_missing_profiles(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Profile = apps.get_model("accounts", "Profile")

    users_with_profiles = Profile.objects.values_list("user_id", flat=True)
    missing_user_ids = User.objects.exclude(
        id__in=users_with_profiles
    ).values_list("id", flat=True)

    Profile.objects.bulk_create(
        Profile(user_id=user_id)
        for user_id in missing_user_ids
    )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_auditlog_ip_address_auditlog_user_agent"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="personal_data_consent",
            field=models.BooleanField(
                default=False,
                verbose_name=(
                    "Согласие на обработку персональных данных"
                ),
            ),
        ),
        migrations.AddField(
            model_name="profile",
            name="personal_data_consent_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Дата согласия",
            ),
        ),
        migrations.RunPython(
            create_missing_profiles,
            migrations.RunPython.noop,
        ),
    ]
