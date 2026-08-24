from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("initiatives", "0007_initiative_moderator_comment"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="initiative",
            index=models.Index(
                fields=["status"],
                name="initiative_status_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="initiative",
            index=models.Index(
                fields=["created_at"],
                name="initiative_created_idx"
            ),
        ),
    ]
