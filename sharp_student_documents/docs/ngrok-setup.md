# ngrok Setup for PayPal Webhooks

## 🚀 Quick Setup with ngrok

### Step 1: Install ngrok
```bash
# Download ngrok from https://ngrok.com/download
# Or install via pip
pip install pyngrok
```

### Step 2: Start ngrok
```bash
# Method 1: Using pyngrok (easier)
python -c "
from pyngrok import ngrok
public_url = ngrok.connect(8000)
print(f'ngrok URL: {public_url}')
print(f'Webhook URL: {public_url}/paypal/webhooks/')
"

# Method 2: Using ngrok CLI
# Download ngrok.exe and run:
ngrok http 8000
```

### Step 3: Get Your HTTPS URL
ngrok will give you:
```
Forwarding  https://abc123.ngrok.io -> http://localhost:8000
```

### Step 4: Use in PayPal
Webhook URL: `https://abc123.ngrok.io/paypal/webhooks/`

## 📱 Alternative Solutions

### Option 2: Local SSL Certificate
```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Run Django with HTTPS
python manage.py runsslserver 0.0.0.0:443 --certificate cert.pem --key key.pem
```

### Option 3: Use webhook.site (for testing only)
1. Go to [webhook.site](https://webhook.site)
2. Copy the provided URL
3. Use it in PayPal for testing
4. Manually forward events to your local server

## 🎯 Recommended: ngrok

### Why ngrok is best:
- ✅ HTTPS automatically
- ✅ Works with localhost
- ✅ Free for development
- ✅ Easy to set up
- ✅ Real-time request inspection

### ngrok Commands:
```bash
# Start ngrok
ngrok http 8000

# Keep it running in background
ngrok http 8000 --log=stdout

# Use custom subdomain (paid)
ngrok http 8000 --subdomain=sharpdocs
```

## 🔧 Django Setup

### Add ngrok to requirements.txt:
```
pyngrok==7.0.0
```

### Test webhook locally:
```python
# views.py
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

@csrf_exempt
def paypal_webhook(request):
    if request.method == 'POST':
        print("Webhook received!")
        print(f"Headers: {dict(request.headers)}")
        print(f"Body: {request.body}")
        
        # Process webhook here
        return JsonResponse({"status": "success"})
    
    return JsonResponse({"error": "Method not allowed"}, status=405)
```

## 📞 Support

- ngrok docs: https://ngrok.com/docs
- PayPal webhook docs: https://developer.paypal.com/docs/api-basics/webhooks/
