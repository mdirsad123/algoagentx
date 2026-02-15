# Razorpay Subscriptions Implementation Guide

This guide covers the implementation of Razorpay subscriptions for AlgoAgentX subscription plans.

## Overview

The Razorpay subscriptions integration allows users to subscribe to PRO, PREMIUM, and ULTIMATE plans with automatic monthly/yearly billing. The implementation includes:

- **Subscription Creation**: Create Razorpay subscriptions for plans
- **Webhook Handling**: Process subscription lifecycle events
- **Credit Management**: Grant monthly included credits
- **Plan Management**: Integration with existing plan catalog

## Architecture

### Components

1. **Razorpay Subscription Service** (`app/services/payments/razorpay_subscription_service.py`)
   - Handles all Razorpay subscription API interactions
   - Manages subscription lifecycle
   - Processes webhooks and grants credits

2. **Subscription API** (`app/api/v1/subscriptions.py`)
   - REST endpoints for subscription operations
   - Input validation and error handling
   - Authentication integration

3. **Plan Catalog Integration** (`app/billing/plan_catalog.py`)
   - Maps plans to Razorpay subscription plans
   - Defines pricing and included credits
   - Validates plan combinations

4. **Database Integration**
   - Extends existing `user_subscriptions` table
   - Tracks Razorpay subscription IDs
   - Manages subscription status lifecycle

## Environment Configuration

Ensure these environment variables are set (same as credit payments):

```bash
# Razorpay Configuration (shared with payments)
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
RAZORPAY_WEBHOOK_SECRET=your_razorpay_webhook_secret
```

## API Endpoints

### 1. Create Subscription
```http
POST /api/v1/subscriptions/razorpay/create
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
  "plan_code": "PRO",
  "billing_period": "MONTHLY"
}
```

**Response:**
```json
{
  "subscription_id": "user_subscription_uuid",
  "razorpay_subscription_id": "sub_123456789",
  "razorpay_key_id": "rzp_test_123456789",
  "status": "TRIALING",
  "start_at": "2024-01-01T00:00:00",
  "end_at": "2024-02-01T00:00:00",
  "trial_end_at": "2024-01-08T00:00:00",
  "included_credits": 500
}
```

### 2. Subscription Webhook
```http
POST /api/v1/subscriptions/razorpay/webhook
X-Razorpay-Signature: signature_hash
Content-Type: application/json

{
  "event": "subscription.activated",
  "payload": {
    "subscription": {
      "entity": {
        "id": "sub_123456789"
      }
    }
  }
}
```

**Response:**
```json
{
  "status": "activated",
  "subscription_id": "user_subscription_uuid",
  "user_id": "user_id",
  "plan_code": "PRO"
}
```

### 3. Get Subscription Status
```http
GET /api/v1/subscriptions/me
Authorization: Bearer <JWT_TOKEN>
```

**Response:**
```json
{
  "subscription_id": "user_subscription_uuid",
  "plan_code": "PRO",
  "billing_period": "MONTHLY",
  "status": "ACTIVE",
  "start_at": "2024-01-01T00:00:00",
  "end_at": "2024-02-01T00:00:00",
  "trial_end_at": "2024-01-08T00:00:00",
  "renews": true,
  "razorpay_subscription_id": "sub_123456789"
}
```

### 4. Cancel Subscription
```http
POST /api/v1/subscriptions/cancel/{subscription_id}
Authorization: Bearer <JWT_TOKEN>
```

**Response:**
```json
{
  "success": true,
  "subscription_id": "subscription_id",
  "status": "CANCELED",
  "message": "Subscription canceled successfully"
}
```

### 5. Get Available Plans
```http
GET /api/v1/subscriptions/plans
```

**Response:**
```json
{
  "plans": {
    "PRO_MONTHLY": {
      "code": "PRO",
      "billing_period": "MONTHLY",
      "price_inr": 999,
      "included_credits": 500,
      "features": {
        "backtests_per_day": 50,
        "ai_runs_per_day": 20,
        "max_parallel_jobs": 3,
        "max_date_range_days": 180,
        "export_enabled": true,
        "support_priority": "MEDIUM"
      },
      "is_active": true
    }
  }
}
```

## Subscription Flow

### 1. Frontend Integration

```javascript
// 1. Get available plans
const plans = await fetch('/api/v1/subscriptions/plans')
  .then(res => res.json());

// 2. Create subscription
const subscription = await fetch('/api/v1/subscriptions/razorpay/create', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    plan_code: 'PRO',
    billing_period: 'MONTHLY'
  })
}).then(res => res.json());

// 3. Handle subscription activation via webhook
// (No frontend action needed - handled server-side)
```

### 2. Webhook Setup

1. **Configure Webhook in Razorpay Dashboard**:
   - Go to Settings → Webhooks
   - Add webhook URL: `https://your-domain.com/api/v1/subscriptions/razorpay/webhook`
   - Set events: `subscription.activated`, `subscription.cancelled`, `subscription.charged`, `subscription.paused`, `subscription.resumed`
   - Set webhook secret (same as RAZORPAY_WEBHOOK_SECRET)

2. **Test Webhook**:
   - Use Razorpay's test webhook feature
   - Verify your endpoint processes events correctly

## Plan Configuration

### Plan Mapping

The system maps AlgoAgentX plans to Razorpay subscription plans:

| AlgoAgentX Plan | Billing Period | Razorpay Plan ID | Price (INR) | Included Credits |
|-----------------|----------------|------------------|-------------|------------------|
| PRO | MONTHLY | plan_pro_monthly | 999 | 500 |
| PRO | YEARLY | plan_pro_yearly | 9999 | 6000 |
| PREMIUM | MONTHLY | plan_premium_monthly | 1999 | 1500 |
| PREMIUM | YEARLY | plan_premium_yearly | 19999 | 18000 |
| ULTIMATE | MONTHLY | plan_ultimate_monthly | 3999 | 5000 |
| ULTIMATE | YEARLY | plan_ultimate_yearly | 39999 | 60000 |

### Credit Granting

Credits are automatically granted in these scenarios:

1. **Initial Trial**: When subscription is created with trial period
2. **Activation**: When subscription becomes active (if not in trial)
3. **Monthly Renewal**: When subscription is charged successfully
4. **Manual Grant**: Can be triggered via webhook events

## Database Schema

### User Subscriptions Table

The existing `user_subscriptions` table is extended with Razorpay fields:

```sql
user_subscriptions (
    id UUID PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    plan_id UUID NOT NULL,
    status VARCHAR(20) NOT NULL,  -- TRIALING, ACTIVE, CANCELED, EXPIRED, PAUSED
    start_at TIMESTAMP WITH TIME ZONE NOT NULL,
    end_at TIMESTAMP WITH TIME ZONE NOT NULL,
    trial_end_at TIMESTAMP WITH TIME ZONE,
    renews BOOLEAN DEFAULT true,
    razorpay_subscription_id VARCHAR(100),
    razorpay_customer_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
)
```

## Webhook Events

### Supported Events

1. **`subscription.activated`**
   - Triggers: When subscription becomes active
   - Action: Update status to ACTIVE, grant credits if not in trial

2. **`subscription.cancelled`**
   - Triggers: When subscription is cancelled
   - Action: Update status to CANCELED

3. **`subscription.charged`**
   - Triggers: When subscription payment is successful
   - Action: Grant monthly credits

4. **`subscription.paused`**
   - Triggers: When subscription is paused
   - Action: Update status to PAUSED

5. **`subscription.resumed`**
   - Triggers: When subscription is resumed
   - Action: Update status to ACTIVE

### Webhook Processing

```python
# Example webhook payload for subscription.activated
{
    "event": "subscription.activated",
    "payload": {
        "subscription": {
            "entity": {
                "id": "sub_123456789",
                "status": "active",
                "plan_id": "plan_pro_monthly",
                "customer_id": "cust_123456789"
            }
        }
    }
}
```

## Security Features

### 1. Signature Verification
- All webhook signatures are verified using Razorpay's HMAC-SHA256 algorithm
- Invalid signatures result in webhook rejection

### 2. Authentication
- All subscription endpoints require JWT authentication
- Users can only access their own subscriptions

### 3. Input Validation
- Plan code and billing period validation
- Subscription ID format validation
- User permission checks

### 4. Idempotent Operations
- Webhook processing is idempotent
- Safe retry mechanisms prevent duplicate credit grants

## Error Handling

### Common Errors

1. **Configuration Errors**:
   - `RAZORPAY_KEY_ID` or `RAZORPAY_KEY_SECRET` not set
   - Returns HTTP 503 Service Unavailable

2. **Invalid Input**:
   - Invalid plan code or billing period
   - Returns HTTP 400 Bad Request

3. **Subscription Not Found**:
   - User tries to access non-existent subscription
   - Returns HTTP 404 Not Found

4. **Permission Errors**:
   - User tries to access another user's subscription
   - Returns HTTP 403 Forbidden

5. **Razorpay API Errors**:
   - Network issues or API rate limits
   - Returns HTTP 500 Internal Server Error

## Testing

### Running Tests

```bash
# Run the subscription test suite
python test_razorpay_subscriptions.py
```

### Test Scenarios

1. **Configuration Test**: Verifies Razorpay is properly configured
2. **Plans Test**: Tests plan retrieval
3. **Subscription Creation**: Tests subscription creation flow
4. **Status Retrieval**: Tests subscription status endpoint
5. **Webhook Processing**: Tests webhook handling

### Manual Testing

1. **Use Razorpay Test Mode**:
   - Set test API keys in environment
   - Use test card details: `4111 1111 1111 1111`
   - Test CVV: `123`, Test expiry: any future date

2. **Test Webhooks**:
   - Use Razorpay dashboard to send test webhook events
   - Verify your endpoint processes them correctly

## Monitoring and Maintenance

### 1. Subscription Status Monitoring
- Monitor for subscriptions stuck in `TRIALING` status
- Set up alerts for failed subscription activations
- Track subscription success rates

### 2. Webhook Monitoring
- Monitor webhook delivery success
- Set up retry mechanisms for failed webhooks
- Track webhook processing times

### 3. Credit Balance Monitoring
- Monitor monthly credit grants
- Track subscription credit usage patterns
- Set up alerts for unusual credit activity

## Troubleshooting

### Common Issues

1. **Subscription Not Activating**:
   - Verify webhook is configured correctly
   - Check webhook secret matches environment variable
   - Ensure subscription plan exists in Razorpay

2. **Credits Not Granted**:
   - Check webhook delivery success
   - Verify credit transaction creation
   - Review error logs for details

3. **Plan Not Found**:
   - Verify plan exists in database
   - Check plan catalog configuration
   - Ensure plan is active

### Debug Mode

Enable debug logging for detailed subscription processing:
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
- Monitor for suspicious subscription patterns

### 3. Performance
- Monitor database performance for subscription queries
- Consider caching frequently accessed plan data
- Set up proper connection pooling

### 4. Monitoring
- Set up application monitoring
- Monitor subscription success rates
- Track webhook delivery and processing

## Integration with Existing Systems

### Credit System Integration
- Automatically grants monthly credits based on plan
- Creates credit transactions for audit trail
- Updates user credit balances in real-time

### Billing Integration
- Uses existing plan catalog and pricing
- Integrates with existing user subscription management
- Maintains consistency with existing billing logic

### Authentication Integration
- Uses existing JWT authentication
- Validates user permissions for subscription operations
- Secure user identification for subscription management

## Next Steps

### For Production Deployment
1. **Set production credentials** in environment
2. **Configure webhooks** in Razorpay dashboard
3. **Set up monitoring** for subscription success rates
4. **Enable HTTPS** for all endpoints
5. **Test with real subscriptions** in test mode

### For Frontend Integration
1. **Implement subscription flow** in frontend application
2. **Add subscription management** UI
3. **Display plan comparison** and features
4. **Handle subscription status** updates

### For Monitoring
1. **Set up alerts** for failed subscriptions
2. **Monitor webhook delivery** success rates
3. **Track subscription churn** and renewal rates
4. **Monitor credit granting** patterns

## Support

For issues with this implementation:
1. Check the application logs
2. Verify Razorpay dashboard for subscription status
3. Test with Razorpay's test mode
4. Review webhook delivery in Razorpay dashboard

For Razorpay-specific issues:
- Visit [Razorpay Support](https://razorpay.com/support/)
- Check [Razorpay Documentation](https://razorpay.com/docs/)