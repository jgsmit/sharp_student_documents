# PayPal Production Setup Guide

## 🚀 Getting Live PayPal Credentials

### Step 1: Create PayPal Developer Account
1. Go to [PayPal Developer Dashboard](https://developer.paypal.com/developer/applications/)
2. Log in with your PayPal business account
3. If you don't have a business account, create one at [PayPal Business](https://www.paypal.com/business)

### Step 2: Create Live Application
1. Click **"Create App"** in the dashboard
2. Select **"Live"** (not Sandbox)
3. Fill in application details:
   - **App Name**: SharpDocs Production
   - **App Type**: Merchant
   - **Email**: Your business email
4. Click **"Create App"**

### Step 3: Get Live Credentials
After creating the app, you'll see:
```
Client ID: live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Client Secret: live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Step 4: Configure Webhooks
1. In your app dashboard, go to **"Webhooks"**
2. Click **"Add Webhook"**
3. **Webhook URL**: `https://yourdomain.com/paypal/webhooks/`
4. **Webhook Events** (select all):
   - PAYMENT.AUTHORIZATION.CREATED
   - PAYMENT.AUTHORIZATION.VOIDED
   - PAYMENT.CAPTURE.COMPLETED
   - PAYMENT.CAPTURE.DENIED
   - PAYMENT.SALE.COMPLETED
   - PAYMENT.SALE.DENIED
   - PAYMENT.SALE.REFUNDED
5. Save and copy the **Webhook ID**

### Step 5: Update Your .env File
```env
# PayPal Live Configuration
PAYPAL_MODE=live
PAYPAL_CLIENT_ID=live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
PAYPAL_CLIENT_SECRET=live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
PAYPAL_WEBHOOK_ID=your_webhook_id_here
```

### Step 6: Test Live Payments
1. **Small test transaction** ($1-5)
2. **Verify webhook delivery**
3. **Check PayPal dashboard** for transactions
4. **Test refund process**

## 🔧 PayPal Business Account Requirements

### Required Documents:
- **Business Registration** documents
- **Bank Account** for payouts
- **Identity Verification** (government ID)
- **Proof of Address** (utility bill, bank statement)

### Account Setup:
1. **Business Information**:
   - Business name and address
   - Contact information
   - Business category

2. **Financial Information**:
   - Bank account for receiving payments
   - Currency preferences

3. **Product/Service Details**:
   - Describe your document marketplace
   - Expected transaction volume
   - Average transaction amount

## 🌍 PayPal Fees (Live)

### Standard Rates (as of 2024):
- **Domestic**: 2.9% + $0.30 USD
- **International**: 4.4% + fixed fee (varies by country)
- **Micropayments** (<$10): 5% + $0.05 USD
- **Digital Goods**: Same as standard rates

### Payout Fees:
- **Standard**: Free (3-5 business days)
- **Instant**: 1% of withdrawal amount

## ⚠️ Important Notes

### Security:
- **Never commit** live credentials to Git
- **Use HTTPS** for webhook URLs
- **Validate webhooks** using PayPal signatures
- **Monitor transactions** regularly

### Compliance:
- **Terms of Service** on your website
- **Privacy Policy** required
- **Refund Policy** clearly stated
- **Customer Support** contact information

### Testing:
- **Use sandbox** for development
- **Test thoroughly** before going live
- **Have rollback plan** ready
- **Monitor first transactions** closely

## 🚨 Before Going Live

### Checklist:
- [ ] PayPal Business account verified
- [ ] Live API credentials obtained
- [ ] Webhooks configured and tested
- [ ] Terms of Service updated
- [ ] Privacy Policy added
- [ ] Refund Policy created
- [ ] SSL certificate installed
- [ ] Test transactions completed
- [ ] Error handling implemented
- [ ] Customer support ready

## 📞 PayPal Support

### Developer Support:
- **Email**: developer@paypal.com
- **Documentation**: [PayPal Developer Docs](https://developer.paypal.com/docs/)
- **Community**: [PayPal Developer Community](https://community.developer.paypal.com/)

### Business Support:
- **Phone**: 1-888-221-1161 (US)
- **Email**: business@paypal.com
- **Help Center**: [PayPal Help Center](https://www.paypal.com/help)

## 🔗 Useful Links

- [PayPal Developer Dashboard](https://developer.paypal.com/developer/applications/)
- [PayPal Business Account](https://www.paypal.com/business)
- [API Documentation](https://developer.paypal.com/docs/api/overview/)
- [Webhooks Guide](https://developer.paypal.com/docs/api-basics/webhooks/)
- [Sandbox Accounts](https://developer.paypal.com/developer/accounts/)
