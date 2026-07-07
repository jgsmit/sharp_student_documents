from django.core.management.base import BaseCommand
from django.utils import timezone
from withdrawals.services import WithdrawalService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Process weekly withdrawals automatically'

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Process regardless of payout day (testing/admin use).",
        )
        parser.add_argument(
            "--ignore-scheduled-date",
            action="store_true",
            help="Include pending withdrawals even if scheduled_for is in the future (testing/admin use).",
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting weekly withdrawal processing...')
        
        try:
            WithdrawalService.process_weekly_withdrawals(
                force=bool(options.get("force")),
                ignore_scheduled_date=bool(options.get("ignore_scheduled_date")),
            )
            self.stdout.write(
                self.style.SUCCESS('Weekly withdrawal processing completed successfully')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Weekly withdrawal processing failed: {str(e)}')
            )
            logger.error(f'Weekly withdrawal processing failed: {str(e)}')
