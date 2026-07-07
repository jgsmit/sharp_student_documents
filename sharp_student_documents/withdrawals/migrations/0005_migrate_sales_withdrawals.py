from datetime import date

from django.db import migrations
from django.utils import timezone


def _next_payout_date(today: date) -> date:
    if today.day <= 14:
        return date(today.year, today.month, 14)
    if today.day <= 28:
        return date(today.year, today.month, 28)
    if today.month == 12:
        return date(today.year + 1, 1, 14)
    return date(today.year, today.month + 1, 14)


def forwards(apps, schema_editor):
    SalesWithdrawal = apps.get_model("sales", "WithdrawalRequest")
    WithdrawalRequest = apps.get_model("withdrawals", "WithdrawalRequest")

    today = timezone.localdate()
    next_payout = _next_payout_date(today)

    # Migrate legacy sales withdrawals into the unified withdrawals system.
    #
    # Safety rules:
    # - Legacy `pending` withdrawals are migrated as `cancelled` to avoid accidental payouts,
    #   and to encourage users to re-request with a verified payout method.
    # - Legacy `approved/processed` are migrated as `completed` for history/analytics.
    # - Legacy `rejected` is migrated as `failed` with a reason.
    for sw in SalesWithdrawal.objects.select_related("wallet", "processed_by").iterator():
        marker = f"migrated_from_sales_id={sw.id}"
        if WithdrawalRequest.objects.filter(admin_notes__contains=marker).exists():
            continue

        status = "failed"
        failure_reason = sw.admin_notes or None
        scheduled_for = None
        processed_at = sw.processed_at
        completed_at = None

        if sw.status in ("approved", "processed"):
            status = "completed"
            failure_reason = None
            completed_at = sw.processed_at
        elif sw.status == "pending":
            status = "cancelled"
            failure_reason = "Legacy pending withdrawal (sales system). Please request again."
            scheduled_for = next_payout
        elif sw.status == "rejected":
            status = "failed"
            failure_reason = sw.admin_notes or "Rejected in legacy sales system."

        admin_notes = sw.admin_notes or ""
        if admin_notes:
            admin_notes = f"{admin_notes}\n{marker}"
        else:
            admin_notes = marker

        WithdrawalRequest.objects.create(
            user=sw.wallet.user,
            withdrawal_method=None,  # Legacy records did not store method info
            amount=sw.amount,
            fee=getattr(sw, "transaction_fee", 0) or 0,
            net_amount=sw.net_amount,
            payout_type="weekly",
            status=status,
            requested_at=sw.created_at,
            processed_at=processed_at,
            completed_at=completed_at,
            scheduled_for=scheduled_for,
            wallet_debited=False,
            admin_notes=admin_notes,
            failure_reason=failure_reason,
        )


def backwards(apps, schema_editor):
    WithdrawalRequest = apps.get_model("withdrawals", "WithdrawalRequest")
    WithdrawalRequest.objects.filter(admin_notes__contains="migrated_from_sales_id=").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("withdrawals", "0004_migrate_instant_to_weekly"),
        ("sales", "0005_alter_withdrawalrequest_commission"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

