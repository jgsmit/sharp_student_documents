from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Test if main.js is loading properly'

    def handle(self, *args, **options):
        self.stdout.write('=== TESTING MAIN.JS LOADING ===')
        
        self.stdout.write('The main.js script is included in base.html, but functions may not be available.')
        self.stdout.write('Let me check if there are any issues with the script loading.')
        
        self.stdout.write('\\nPossible issues:')
        self.stdout.write('1. Script not loaded due to CSP errors')
        self.stdout.write('2. Script loaded but functions not in global scope')
        self.stdout.write('3. Script loaded after page load, functions not available')
        self.stdout.write('4. Browser cache issues')
        
        self.stdout.write('\\nDebugging steps:')
        self.stdout.write('1. Open Developer Tools (F12)')
        self.stdout.write('2. Go to Network tab')
        self.stdout.write('3. Reload the page')
        self.stdout.write('4. Check if main.js is loaded (status 200)')
        self.stdout.write('5. Check Console for JavaScript errors')
        
        self.stdout.write('\\nIf main.js is loaded but functions not available:')
        self.stdout.write('1. Check Console tab for errors')
        self.stdout.write('2. Look for "Uncaught ReferenceError"')
        self.stdout.write('3. Look for "getCookie is not defined"')
        self.stdout.write('4. Look for "SharpDocs is not defined"')
        
        self.stdout.write('\\nQuick test in Console:')
        self.stdout.write('console.log("Testing main.js loading");')
        self.stdout.write('console.log(typeof window.SharpDocs);')
        self.stdout.write('console.log(typeof window.approveWithdrawal);')
        
        self.stdout.write('\\nExpected results:')
        self.stdout.write('"Testing main.js loading" - should appear in console')
        self.stdout.write('typeof window.SharpDocs - should be "object"')
        self.stdout.write('typeof window.approveWithdrawal - should be "function"')
        
        self.stdout.write('\\n=== TEST COMPLETE ===')
