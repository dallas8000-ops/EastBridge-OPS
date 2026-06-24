from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0003_pgvector"),
    ]

    operations = [
        migrations.AddField(
            model_name="evidencedocument",
            name="embedding_model",
            field=models.CharField(blank=True, max_length=128),
        ),
    ]
