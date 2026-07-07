from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0004_rename_documents_re_status_0e2e84_idx_documents_r_status_ad38e7_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="license_type",
            field=models.CharField(
                choices=[
                    ("all_rights_reserved", "All rights reserved"),
                    ("personal_use_only", "Personal use only (no redistribution)"),
                    ("cc_by", "Creative Commons - Attribution (CC BY)"),
                    ("cc_by_nc", "Creative Commons - Attribution-NonCommercial (CC BY-NC)"),
                ],
                default="all_rights_reserved",
                help_text="Usage rights for buyers (shown on the listing and download areas).",
                max_length=40,
            ),
        ),
        migrations.AddField(
            model_name="document",
            name="license_note",
            field=models.TextField(
                blank=True,
                help_text="Optional extra terms (e.g., 'One-device only', 'No sharing', 'For personal study').",
            ),
        ),
    ]

