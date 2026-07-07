from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0005_document_license_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="document",
            name="file",
            field=models.FileField(max_length=500, upload_to="documents/"),
        ),
    ]
