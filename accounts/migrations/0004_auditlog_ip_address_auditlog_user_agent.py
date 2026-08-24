from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_notification"),
    ]

    operations = [
        migrations.AddField(
            model_name="auditlog",
            name="ip_address",
            field=models.GenericIPAddressField(
                blank=True,
                null=True,
                verbose_name="IP-адрес"
            ),
        ),
        migrations.AddField(
            model_name="auditlog",
            name="user_agent",
            field=models.TextField(
                blank=True,
                default="",
                verbose_name="User-Agent"
            ),
        ),
    ]
