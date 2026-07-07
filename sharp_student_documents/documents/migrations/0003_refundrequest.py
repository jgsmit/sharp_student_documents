from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0002_backfill_paid_order_amount_paid"),
    ]

    operations = [
        migrations.CreateModel(
            name="RefundRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("open", "Open"),
                            ("admin_review", "Admin Review"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                            ("refunded", "Refunded"),
                        ],
                        db_index=True,
                        default="open",
                        max_length=20,
                    ),
                ),
                (
                    "reason",
                    models.CharField(
                        choices=[
                            ("not_as_described", "Not as described"),
                            ("wrong_level", "Wrong academic level"),
                            ("corrupt_file", "File is corrupt / won't open"),
                            ("duplicate", "Duplicate / already owned"),
                            ("other", "Other"),
                        ],
                        max_length=30,
                    ),
                ),
                ("details", models.TextField(blank=True)),
                ("paypal_refund_id", models.CharField(blank=True, max_length=255, null=True)),
                ("admin_notes", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                (
                    "buyer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="refund_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "order",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="refund_request",
                        to="documents.order",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="refundrequest",
            index=models.Index(fields=["status", "created_at"], name="documents_re_status_0e2e84_idx"),
        ),
        migrations.AddIndex(
            model_name="refundrequest",
            index=models.Index(fields=["buyer", "created_at"], name="documents_re_buyer_i_8b2c1b_idx"),
        ),
    ]

