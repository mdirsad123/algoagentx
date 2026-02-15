# Razorpay Payments Implementation Guide

This guide covers the implementation of Razorpay payments for buying credit packs in AlgoAgentX.

## Overview

The Razorpay integration allows users to purchase credit packs using Razorpay's payment gateway. The implementation includes:

- **Order Creation**: Create Razorpay orders for credit purchases
- **Payment Verification**: Verify payment signatures and grant credits
- **Webhook Handling**: Process payment captured events via webhooks
- **Credit Management**: Automatically grant credits after successful payments

## Architecture

### Components

1. **Razorpay Service** (`app/services/payments/razorpay_service.py`)
   - Handles all Razorpay API interactions
   - Manages payment lifecycle
   - Processes webhooks

2. **Payment API** (`app/api/v1/payments.py`)
   - REST endpoints for payment operations
   - Input validation and error handling
   - Authentication integration

3. **Payment Model** (`app/db/models/payments.py`)
   - Database schema for payment records
   - Tracks payment status and Razorpay IDs

4. **Payment Schemas** (`app/schemas/payments.py`)
   - Pydantic models for API requests/responses
   - Input validation and serialization

## Environment Configuration

Add these environment variables to your `.env` file:

```bash
# Razorpay Configuration
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
RAZORPAY_WEBHOOK_SECRET=your_razorpay_webhook_secret
```

### Getting Razorpay Credentials

1. **Sign up for Razorpay**: Visit [razorpay.com](https://razorpay.com/) and create an account
2. **Get API Keys**: In your Razorpay dashboard, go to Settings → API Keys
3. **Generate Test Keys**: Use test keys for development, live keys for production
4. **Set Webhook Secret**: Configure webhooks in your Razorpay dashboard and set a secret

## API Endpoints

### 1. Create Order
```http
POST /api/v1/payments/razorpay/create-order
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
  "credits_to_buy": 10
}
```

**Response:**
```json
{
  "order_id": "order_123456789",
  "amount": 1000,
  "currency": "INR",
  "razorpay_key_id": "rzp_test_123456789"
}
```

### 2. Verify Payment
```http
POST /api/v1/payments/razorpay/verify
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
  "order_id": "order_123456789",
  "razorpay_payment_id": "pay_123456789",
  "razorpay_signature": "signature_hash"
}
```

**Response:**
```json
{
  "success": true,
  "payment_id": "payment_uuid",
  "credits_granted": 10,
  "message": "Payment verified and credits granted successfully"
}
```

### 3. Webhook Handler
```http
POST /api/v1/payments/razorpay/webhook
X-Razorpay-Signature: signature_hash
Content-Type: application/json

{
  "event": "payment.captured",
  "payload": {
    "payment": {
      "entity": {
        "id": "pay_123456789",
        "order_id": "order_123456789",
        "status": "captured"
      }
    }
  }
}
```

**Response:**
```json
{
  "status": "processed",
  "payment_id": "payment_uuid",
  "credits_granted": 10,
  "message": "Webhook processed and credits granted successfully"
}
```

### 4. Get Configuration
```http
GET /api/v1/payments/razorpay/config
```

**Response:**
```json
{
  "key_id": "rzp_test_123456789",
  "configured": true
}
```

## Payment Flow

### 1. Frontend Integration

```javascript
// 1. Get Razorpay configuration
const config = await fetch('/api/v1/payments/razorpay/config')
  .then(res => res.json());

// 2. Create order
const order = await fetch('/api/v1/payments/razorpay/create-order', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ credits_to_buy: 10 })
}).then(res => res.json());

// 3. Open Razorpay checkout
const options = {
  key: config.key_id,
  amount: order.amount,
  currency: order.currency,
  name: 'AlgoAgentX',
  description: 'Credit Topup',
  order_id: order.order_id,
  handler: function(response) {
    // 4. Verify payment
    fetch('/api/v1/payments/razorpay/verify', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        order_id: order.order_id,
        razorpay_payment_id: response.razorpay_payment_id,
        razorpay_signature: response.razorpay_signature
      })
    }).then(res => res.json())
      .then(data => {
        if (data.success) {
          alert('Payment successful! Credits granted.');
        }
      });
  },
  prefill: {
    name: 'Customer Name',
    email: 'customer@example.com',
    contact: '9999999999'
  },
  theme: {
    color: '#3399cc'
  }
};

const rzp = new Razorpay(options);
rzp.open();
```

### 2. Webhook Setup

1. **Configure Webhook in Razorpay Dashboard**:
   - Go to Settings → Webhooks
   - Add webhook URL: `https://your-domain.com/api/v1/payments/razorpay/webhook`
   - Set events: `payment.captured`
   - Set webhook secret

2. **Test Webhook**:
   - Use Razorpay's test webhook feature
   - Verify your endpoint receives and processes events correctly

## Pricing Logic

The current implementation uses a simple pricing model:
- **1 Credit = ₹1**
- Amount is calculated in paise (100 paise = ₹1)

### Customizing Pricing

To implement different pricing tiers or bulk discounts, modify the `calculate_amount_inr` method in `RazorpayService`:

```python
def calculate_amount_inr(self, credits_to_buy: int) -> int:
    """
    Calculate amount in INR for given credits.
    Customize this method for different pricing tiers.
    """
    # Example: Bulk discount pricing
    if credits_to_buy >= 100:
        rate = 0.9  # 10% discount for 100+ credits
    elif credits_to_buy >= 50:
        rate = 0.95  # 5% discount for 50+ credits
    else:
        rate = 1.0  # Standard rate
    
    amount_in_paise = int(credits_to_buy * 100 * rate)
    return amount_in_paise
```

## Security Features

### 1. Signature Verification
- All payment signatures are verified using Razorpay's HMAC-SHA256 algorithm
- Webhook signatures are verified using the configured webhook secret
- Invalid signatures result in payment rejection

### 2. Idempotent Operations
- Payment verification is idempotent - multiple verifications of the same payment are safe
- Webhook processing checks for already-processed payments
- Prevents duplicate credit grants

### 3. Environment Separation
- Test and production environments use different API keys
- Webhook secrets are environment-specific
- Configuration validation prevents misconfiguration

## Error Handling

### Common Errors

1. **Configuration Errors**:
   - `RAZORPAY_KEY_ID` or `RAZORPAY_KEY_SECRET` not set
   - Returns HTTP 503 Service Unavailable

2. **Invalid Input**:
   - `credits_to_buy` <= 0
   - Returns HTTP 400 Bad Request

3. **Signature Verification**:
   - Invalid payment signature
   - Invalid webhook signature
   - Returns HTTP 400 Bad Request

4. **Payment Processing**:
   - Payment record not found
   - Database errors
   - Returns HTTP 500 Internal Server Error

### Logging

All payment operations are logged for debugging and monitoring:
- Order creation
- Payment verification
- Webhook processing
- Error conditions

## Testing

### Running Tests

```bash
# Run the payment test suite
python test_razorpay_payments.py
```

### Test Scenarios

1. **Configuration Test**: Verifies Razorpay is properly configured
2. **Order Creation**: Tests order creation endpoint
3. **Payment Verification**: Tests payment verification flow
4. **Webhook Processing**: Tests webhook handling

### Manual Testing

1. **Use Razorpay Test Mode**:
   - Set test API keys in environment
   - Use test card details: `4111 1111 1111 1111`
   - Test CVV: `123`, Test expiry: any future date

2. **Test Webhooks**:
   - Use Razorpay dashboard to send test webhook events
   - Verify your endpoint processes them correctly

## Database Schema

### Payments Table

```sql
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(36) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    purpose VARCHAR(50) NOT NULL,
    amount_inr INTEGER NOT NULL,
    currency VARCHAR(3) DEFAULT 'INR',
    status VARCHAR(20) NOT NULL,
    razorpay_order_id VARCHAR(100),
    razorpay_payment_id VARCHAR(100),
    razorpay_signature VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Indexes

Consider adding indexes for performance:
```sql
CREATE INDEX idx_payments_user_id ON payments(user_id);
CREATE INDEX idx_payments_razorpay_order_id ON payments(razorpay_order_id);
CREATE INDEX idx_payments_status ON payments(status);
```

## Monitoring and Maintenance

### 1. Payment Status Monitoring
- Monitor for payments stuck in `CREATED` status
- Set up alerts for failed payments
- Track payment success rates

### 2. Webhook Monitoring
- Monitor webhook delivery success
- Set up retry mechanisms for failed webhooks
- Track webhook processing times

### 3. Credit Balance Monitoring
- Monitor user credit balances
- Track credit topup patterns
- Set up alerts for unusual activity

## Troubleshooting

### Common Issues

1. **Signature Verification Failures**:
   - Verify API keys are correct
   - Check webhook secret configuration
   - Ensure no extra whitespace in signatures

2. **Payment Not Found**:
   - Verify order_id matches created order
   - Check payment record exists in database
   - Ensure user authentication is working

3. **Credits Not Granted**:
   - Check database transaction commits
   - Verify user credit record creation
   - Review error logs for details

### Debug Mode

Enable debug logging for detailed payment processing information:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Production Deployment

### 1. Environment Variables
- Set production API keys
- Configure production webhook secret
- Ensure proper environment separation

### 2. Security
- Use HTTPS for all endpoints
- Secure webhook endpoint with IP whitelisting if possible
- Monitor for suspicious payment patterns

### 3. Performance
- Monitor database performance for payment queries
- Consider caching frequently accessed payment data
- Set up proper connection pooling

### 4. Monitoring
- Set up application monitoring
- Monitor payment success rates
- Track webhook delivery and processing

## Support

For issues with this implementation:
1. Check the application logs
2. Verify Razorpay dashboard for payment status
3. Test with Razorpay's test mode
4. Review webhook delivery in Razorpay dashboard

For Razorpay-specific issues:
- Visit [Razorpay Support](https://razorpay.com/support/)
- Check [Razorpay Documentation](https://razorpay.com/docs/)