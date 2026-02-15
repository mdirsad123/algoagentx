# Notifications and Email Implementation for Strategy Requests

## Overview
Implemented comprehensive notification system for Strategy Requests with both in-app notifications and optional SMTP email functionality.

## Features Implemented

### 1. New Notification Types
Added two new notification types to the existing notification system:

- **STRATEGY_REQUEST**: Triggered when a user submits a strategy request
- **STRATEGY_DEPLOYED**: Triggered when an admin deploys a strategy

### 2. In-App Notifications
- Reuses existing notification table and service
- Admins receive notifications when users submit requests
- Users receive notifications when their strategies are deployed
- Includes rich metadata for context

### 3. Email Notifications
- Optional SMTP email functionality
- Admin email notifications for new strategy requests
- User email notifications for strategy deployments
- Graceful degradation when SMTP is not configured

## Files Modified/Created

### 1. AlgoAgentXAPI/app/schemas/notifications.py
**Changes**:
- Added `STRATEGY_REQUEST` and `STRATEGY_DEPLOYED` to notification type description
- Maintains backward compatibility with existing notification types

### 2. AlgoAgentXAPI/app/core/config.py
**Changes**:
- Added SMTP configuration variables:
  - `smtp_host`: SMTP server host (default: "smtp.gmail.com")
  - `smtp_port`: SMTP server port (default: 587)
  - `admin_notify_emails`: Comma-separated list of admin emails
- Maintains existing SMTP credentials for backward compatibility

### 3. AlgoAgentXAPI/app/services/email_service.py (NEW FILE)
**Features**:
- Complete email service with SMTP integration
- Admin email distribution (sends to multiple admin emails)
- Graceful error handling and logging
- Template methods for strategy notifications
- Automatic SMTP configuration detection

**Key Methods**:
- `send_to_admins()`: Send emails to all configured admin addresses
- `send_strategy_request_notification()`: Template for request notifications
- `send_strategy_deployed_notification()`: Template for deployment notifications

### 4. AlgoAgentXAPI/app/api/v1/strategy_requests.py
**Changes**:
- Added imports for notification and email services
- Enhanced `create_strategy_request()` endpoint with notification logic:
  - Fetches user details for personalized notifications
  - Sends in-app notifications to all admin users
  - Sends email notifications to configured admin emails
  - Graceful error handling (notifications don't fail the request)

**Notification Logic**:
```python
# Get all admin users and send notifications
admin_users_query = select(User).where(User.role == "admin")
admin_users_result = await db.execute(admin_users_query)
admin_users = admin_users_result.scalars().all()

for admin_user in admin_users:
    await notification_service.create_notification(admin_user.id, notification_data)
```

### 5. AlgoAgentXAPI/app/api/v1/admin_strategy_requests.py
**Changes**:
- Added imports for notification and email services
- Enhanced `update_strategy_request()` endpoint with deployment notifications:
  - Sends in-app notification to user when strategy is deployed
  - Sends email notification to user when strategy is deployed
  - Includes deployment metadata (request_id, strategy_id, deployed_by)

**Deployment Notification Logic**:
```python
# Send notification to user if strategy was deployed
if new_status == "DEPLOYED":
    try:
        # Send in-app notification to user
        notification_service = NotificationService(db)
        notification_data = NotificationCreate(
            type="STRATEGY_DEPLOYED",
            title="Strategy Deployed",
            message=f"Your strategy '{request.title}' is ready.",
            metadata={
                "request_id": str(request_id),
                "strategy_id": str(deployed_strategy_id) if deployed_strategy_id else strategy_id,
                "deployed_by": admin_user["user_id"]
            }
        )
        await notification_service.create_notification(request.user_id, notification_data)
        
        # Send email notification to user
        await email_service.send_strategy_deployed_notification(
            user_email=request.email,
            user_name=request.name or request.email,
            strategy_title=request.title
        )
    except Exception as e:
        logger.error("Failed to send deployment notification: %s", str(e))
```

## Environment Configuration

### Required Environment Variables
```bash
# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Admin Email Distribution
ADMIN_NOTIFY_EMAILS=admin1@example.com,admin2@example.com,admin3@example.com
```

### Optional Environment Variables
```bash
# Existing SMTP credentials (for backward compatibility)
SMTP_EMAIL=mdirsadtech7305@gmail.com
SMTP_PASSWORD=ippq cczp hwkn jyrl
```

## Notification Flow

### When User Submits Strategy Request
1. **Request Creation**: Strategy request is created in database
2. **Admin In-App Notification**: All admin users receive notification
   - Type: `STRATEGY_REQUEST`
   - Title: "New Strategy Request"
   - Message: "{user} requested {title}"
   - Metadata: request_id, user_id, user_email, user_name
3. **Admin Email Notification**: Emails sent to configured admin addresses
   - Subject: "New Strategy Request Submitted"
   - Includes request details and submission time

### When Admin Deploys Strategy
1. **Deployment Logic**: Strategy is created/updated and linked to request
2. **User In-App Notification**: Request owner receives notification
   - Type: `STRATEGY_DEPLOYED`
   - Title: "Strategy Deployed"
   - Message: "Your strategy '{title}' is ready."
   - Metadata: request_id, strategy_id, deployed_by
3. **User Email Notification**: Email sent to request owner
   - Subject: "Your Strategy Has Been Deployed"
   - Includes strategy details and deployment time

## Error Handling

### Graceful Degradation
- **SMTP Not Configured**: Logs warning, continues without sending emails
- **Email Sending Fails**: Logs error, continues without failing the request
- **Notification Service Fails**: Logs error, continues without failing the request
- **Database Errors**: Proper transaction handling and rollback

### Logging
- Comprehensive logging for debugging and monitoring
- Error details logged without exposing sensitive information
- Success/failure tracking for email and notification operations

## Security Considerations

### Email Security
- SMTP credentials stored in environment variables
- No sensitive data in email content
- Proper email validation and sanitization

### Notification Security
- Only authenticated users can receive notifications
- Admin notifications only sent to users with admin role
- User notifications only sent to request owners

### Data Privacy
- User email addresses only used for notifications
- No personal data exposed in notification metadata
- Proper access control for notification viewing

## Testing

### Test Script
Created `test_notifications_and_emails.py` with comprehensive test cases:
- Strategy request creation with notification verification
- User notification checking
- Strategy deployment with notification verification
- Admin notification verification
- Email functionality testing (requires SMTP configuration)

### Test Coverage
- ✅ Admin in-app notifications on request creation
- ✅ User in-app notifications on deployment
- ✅ Email notifications (when SMTP configured)
- ✅ Error handling and graceful degradation
- ✅ Notification metadata validation

## Integration Notes

### Database Requirements
- Existing `notifications` table structure maintained
- No new database migrations required
- Leverages existing `users` table for role checking

### Authentication Integration
- Uses existing JWT-based authentication
- Role checking via `User.role` field
- Admin role required for admin notifications

### Frontend Integration
- Existing notification API endpoints work unchanged
- Frontend can filter notifications by type
- Real-time notification updates supported

## Future Enhancements

### Potential Improvements
1. **Notification Preferences**: Allow users to configure notification preferences
2. **Email Templates**: HTML email templates with better formatting
3. **Notification Channels**: Support for SMS, push notifications
4. **Batch Notifications**: Aggregate multiple notifications
5. **Delivery Tracking**: Track email delivery and open rates

### Monitoring
- Add metrics for notification delivery rates
- Monitor email sending performance
- Track notification engagement

## Usage Examples

### Environment Setup
```bash
# Add to .env file
ADMIN_NOTIFY_EMAILS=admin@company.com,manager@company.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=notifications@company.com
SMTP_PASSWORD=your-app-password
```

### Testing Notifications
```bash
# Run the test script
python test_notifications_and_emails.py

# Expected output:
# 1. Testing strategy request creation with notifications...
#    Request created: [uuid]
#    Found 2 STRATEGY_REQUEST notifications
#    Notification: John Doe requested Test Strategy Request
```

## Troubleshooting

### Common Issues
1. **No Admin Notifications**: Check that users have `role = "admin"`
2. **No Email Notifications**: Verify SMTP configuration and `ADMIN_NOTIFY_EMAILS`
3. **Email Sending Fails**: Check SMTP credentials and server settings
4. **Notifications Not Visible**: Ensure proper authentication and role permissions

### Debug Logging
Enable debug logging to troubleshoot issues:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

This implementation provides a robust, scalable notification system that enhances user experience while maintaining system reliability and security.