from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Test withdrawal approval function availability'

    def handle(self, *args, **options):
        self.stdout.write('=== TESTING WITHDRAWAL APPROVAL FUNCTION ===')
        
        self.stdout.write('The approveWithdrawal function has been added to main.js')
        self.stdout.write('To test it, follow these steps:')
        
        self.stdout.write('\\n1. Go to: http://127.0.0.1:8000/documents/admin/manage-withdrawals/')
        self.stdout.write('2. Login as admin: admin / admin123')
        self.stdout.write('3. Open Developer Tools (F12)')
        self.stdout.write('4. Click Console tab')
        self.stdout.write('5. Run: approveWithdrawal("d549536d-b150-4d76-80f7-bc993b1133a0")')
        
        self.stdout.write('\\nExpected result:')
        self.stdout.write('- Confirmation dialog should appear')
        self.stdout.write('- If you click OK, the withdrawal should be processed')
        self.stdout.write('- Status should change to "Processing..." then "Completed" or "Failed"')
        
        self.stdout.write('\\nIf you get "approveWithdrawal is not defined":')
        self.stdout.write('- Clear browser cache (Ctrl+Shift+R)')
        self.stdout.write('- Refresh the page')
        self.stdout.write('- Try again')
        
        self.stdout.write('\\n=== TEST COMPLETE ===')
