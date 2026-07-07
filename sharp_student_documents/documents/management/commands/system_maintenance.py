from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db import connection
from django.core.mail import send_mail
from django.conf import settings
import os
import shutil
from datetime import datetime


class Command(BaseCommand):
    help = 'Run system maintenance tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--task',
            type=str,
            choices=['database', 'email', 'security', 'backup', 'all'],
            default='all',
            help='Specific maintenance task to run'
        )

    def handle(self, *args, **options):
        task = options['task']
        
        if task == 'all':
            self.run_database_maintenance()
            self.run_email_queue_processing()
            self.run_security_audit()
            self.run_backup_system()
        elif task == 'database':
            self.run_database_maintenance()
        elif task == 'email':
            self.run_email_queue_processing()
        elif task == 'security':
            self.run_security_audit()
        elif task == 'backup':
            self.run_backup_system()

    def run_database_maintenance(self):
        """Perform database maintenance operations"""
        self.stdout.write('Running database maintenance...')
        
        try:
            from django.core.management import call_command
            
            # Clean up old sessions
            call_command('clearsessions')
            self.stdout.write('✓ Cleared old sessions')
            
            # Optimize database tables (for SQLite)
            with connection.cursor() as cursor:
                cursor.execute("VACUUM;")
                cursor.execute("ANALYZE;")
            self.stdout.write('✓ Optimized database tables')
            
            # Clean up old download logs (older than 90 days)
            try:
                from sharp_student_documents.models import DownloadLog
                cutoff_date = timezone.now() - timedelta(days=90)
                deleted_logs = DownloadLog.objects.filter(download_time__lt=cutoff_date).delete()[0]
                self.stdout.write(f'✓ Cleaned {deleted_logs} old download logs')
            except Exception as e:
                self.stdout.write(f'⚠ Could not clean download logs: {e}')
            
            # Clean up old security logs (older than 180 days)
            try:
                from security.models import SecurityLog
                security_cutoff = timezone.now() - timedelta(days=180)
                deleted_security_logs = SecurityLog.objects.filter(created_at__lt=security_cutoff).delete()[0]
                self.stdout.write(f'✓ Cleaned {deleted_security_logs} old security logs')
            except Exception as e:
                self.stdout.write(f'⚠ Could not clean security logs: {e}')
            
            self.stdout.write(self.style.SUCCESS('Database maintenance completed successfully'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Database maintenance failed: {e}'))

    def run_email_queue_processing(self):
        """Process pending email queue"""
        self.stdout.write('Processing email queue...')
        
        try:
            from withdrawals.models import AdminNotification
            
            # Get pending notifications that need email sending
            pending_notifications = AdminNotification.objects.filter(
                is_read=False,
                created_at__gte=timezone.now() - timedelta(hours=24)
            )
            
            sent_count = 0
            for notification in pending_notifications:
                if hasattr(notification, 'requires_email') and notification.requires_email:
                    try:
                        send_mail(
                            subject=f'SharpDocs: {notification.title}',
                            message=notification.message,
                            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'admin@sharpdocs.com'),
                            recipient_list=[getattr(settings, 'ADMIN_EMAIL', 'admin@sharpdocs.com')],
                            fail_silently=False,
                        )
                        if hasattr(notification, 'email_sent'):
                            notification.email_sent = True
                            notification.save()
                        sent_count += 1
                    except Exception as e:
                        self.stdout.write(f'⚠ Failed to send email for notification {notification.id}: {e}')
            
            self.stdout.write(f'✓ Sent {sent_count} emails')
            self.stdout.write(self.style.SUCCESS('Email queue processing completed'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Email queue processing failed: {e}'))

    def run_security_audit(self):
        """Run security audit checks"""
        self.stdout.write('Running security audit...')
        
        try:
            audit_results = []
            
            # Check for suspicious login patterns
            try:
                from security.models import SecurityLog
                from django.db.models import Count
                
                recent_failed_logins = SecurityLog.objects.filter(
                    event_type='LOGIN_FAILED',
                    created_at__gte=timezone.now() - timedelta(hours=24)
                ).values('ip_address').annotate(
                    failed_count=Count('id')
                ).filter(failed_count__gt=5)
                
                if recent_failed_logins:
                    audit_results.append(f'Found {len(recent_failed_logins)} IPs with suspicious login attempts')
            except Exception as e:
                self.stdout.write(f'⚠ Could not check login patterns: {e}')
            
            # Check for users without 2FA (should be enabled for admins)
            try:
                from accounts.models import CustomUser
                admins_without_2fa = CustomUser.objects.filter(
                    is_staff=True,
                    two_factor__isnull=True
                ).count()
                
                if admins_without_2fa > 0:
                    audit_results.append(f'{admins_without_2fa} admin accounts without 2FA protection')
            except Exception as e:
                self.stdout.write(f'⚠ Could not check 2FA status: {e}')
            
            # Check for pending identity verifications older than 7 days
            try:
                from security.models import IdentityVerification
                old_pending_verifications = IdentityVerification.objects.filter(
                    status='PENDING',
                    created_at__lt=timezone.now() - timedelta(days=7)
                ).count()
                
                if old_pending_verifications > 0:
                    audit_results.append(f'{old_pending_verifications} identity verifications pending for over 7 days')
            except Exception as e:
                self.stdout.write(f'⚠ Could not check identity verifications: {e}')
            
            # Check for unusual document upload patterns
            try:
                from documents.models import Document
                recent_uploads = Document.objects.filter(
                    created_at__gte=timezone.now() - timedelta(hours=1)
                ).values('seller').annotate(
                    upload_count=Count('id')
                ).filter(upload_count__gt=10)
                
                if recent_uploads:
                    audit_results.append(f'Found {len(recent_uploads)} users with unusual upload patterns')
            except Exception as e:
                self.stdout.write(f'⚠ Could not check upload patterns: {e}')
            
            if audit_results:
                self.stdout.write(self.style.WARNING(f'Security audit found {len(audit_results)} issues:'))
                for result in audit_results:
                    self.stdout.write(f'  ⚠ {result}')
            else:
                self.stdout.write(self.style.SUCCESS('Security audit completed - no critical issues found'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Security audit failed: {e}'))

    def run_backup_system(self):
        """Create system backups"""
        self.stdout.write('Creating system backups...')
        
        try:
            from django.core.management import call_command
            from django.conf import settings
            
            # Create backup directory if it doesn't exist
            backup_dir = os.path.join(settings.BASE_DIR, 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Database backup
            db_backup_file = os.path.join(backup_dir, f'db_backup_{timestamp}.json')
            with open(db_backup_file, 'w', encoding='utf-8') as f:
                call_command('dumpdata', stdout=f)
            self.stdout.write(f'✓ Database backup created: {db_backup_file}')
            
            # Media files backup
            media_backup_dir = os.path.join(backup_dir, f'media_backup_{timestamp}')
            if hasattr(settings, 'MEDIA_ROOT') and os.path.exists(settings.MEDIA_ROOT):
                shutil.copytree(settings.MEDIA_ROOT, media_backup_dir)
                self.stdout.write(f'✓ Media backup created: {media_backup_dir}')
            else:
                self.stdout.write('⚠ Media directory not found or not configured')
            
            # Clean up old backups (keep last 10)
            all_backups = [f for f in os.listdir(backup_dir) if f.startswith('db_backup_')]
            all_backups.sort()
            if len(all_backups) > 10:
                for old_backup in all_backups[:-10]:
                    old_path = os.path.join(backup_dir, old_backup)
                    if os.path.isfile(old_path):
                        os.remove(old_path)
                        self.stdout.write(f'✓ Removed old backup: {old_backup}')
            
            self.stdout.write(self.style.SUCCESS('System backup completed successfully'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'System backup failed: {e}'))
