# Admin User Setup Guide

This guide explains how to create and manage admin users for AlgoAgentX.

## Overview

AlgoAgentX uses role-based access control with the following roles:
- `admin` - Full administrative access to all admin APIs and dashboard
- `user` - Standard user with access to main application features

## Creating an Admin User

### Method 1: CLI Script (Recommended)

Use the provided CLI script to create an admin user safely.

#### Prerequisites
- Python 3.11+
- Environment variables set up
- Database connection available

#### Steps

1. **Set environment variables:**
   ```bash
   export ADMIN_EMAIL="admin@example.com"
   export ADMIN_PASSWORD="SecurePassword123!"
   ```

2. **Run the admin creation script:**
   ```bash
   cd AlgoAgentXAPI
   python scripts/create_admin.py
   ```

3. **Verify creation:**
   ```
   ✅ Admin user created successfully!
      Email: admin@example.com
      User ID: 123e4567-e89b-12d3-a456-426614174000
      Role: admin
      Created at: 2024-01-01 12:00:00
   ```

#### Security Notes
- This script **cannot** be run in production environment
- Password must be at least 8 characters long
- Email format is validated
- Script prevents duplicate admin creation with same email

### Method 2: Manual Database Insert (Development Only)

For development/testing purposes only:

```sql
INSERT INTO users (id, email, password_hash, role, fullname, created_at) 
VALUES (
    'your-uuid-here',
    'admin@example.com', 
    '$2b$12$hashed_password_here',
    'admin',
    'Admin User',
    NOW()
);
```

**⚠️ Warning:** Never use this method in production. Always use the CLI script.

## Admin API Access

### Authentication
Admin APIs require JWT authentication. Use the standard login endpoint:

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "SecurePassword123!"
  }'
```

### Admin Endpoints
All admin endpoints are protected and require admin role:

- `GET /api/v1/admin/metrics` - Dashboard metrics
- `GET /api/v1/admin/users` - User management
- `GET /api/v1/admin/payments` - Payment management
- `GET /api/v1/admin/subscriptions` - Subscription management
- `GET /api/v1/admin/credits` - Credit transactions
- `GET /api/v1/admin/support-tickets` - Support tickets
- `PUT /api/v1/admin/users/{user_id}/status` - User status control

### Example Admin Request
```bash
curl -X GET "http://localhost:8000/api/v1/admin/metrics" \
  -H "Authorization: Bearer your_jwt_token_here"
```

## Security Best Practices

### Production Environment
1. **Use secure admin credentials:**
   - Strong, unique passwords
   - Consider using password managers
   - Rotate passwords regularly

2. **Limit admin access:**
   - Only create admin users when absolutely necessary
   - Monitor admin API usage
   - Implement audit logging

3. **Environment security:**
   - Never commit admin credentials to version control
   - Use environment variables or secret management systems
   - Restrict database access

### Development Environment
1. **Use different credentials:**
   - Never reuse production admin credentials
   - Use development-specific email addresses

2. **Regular cleanup:**
   - Remove unused admin accounts
   - Reset admin passwords periodically

## Troubleshooting

### Common Issues

**"Admin creation script cannot be run in production"**
- This is intentional security measure
- Use secure database management tools in production
- Consider using migration scripts with proper access controls

**"User with email already exists"**
- Admin user already created with that email
- Use different email address or check existing users

**"Invalid email format"**
- Ensure email contains @ and . characters
- Example: admin@company.com

**"Password must be at least 8 characters"**
- Admin passwords require minimum 8 characters
- Use strong, complex passwords

### Getting Help

If you encounter issues:

1. Check application logs for detailed error messages
2. Verify database connectivity
3. Ensure environment variables are properly set
4. Confirm you're not in production environment (for CLI script)

## API Reference

### Admin User Schema
```json
{
  "id": "uuid",
  "email": "string",
  "role": "admin",
  "fullname": "string",
  "created_at": "datetime"
}
```

### Admin Authentication Response
```json
{
  "access_token": "jwt_token",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "admin@example.com",
    "role": "admin",
    "fullname": "Admin User",
    "displayName": "Admin User"
  }
}
```

## Related Documentation

- [User Management](user_management.md)
- [API Authentication](api_authentication.md)
- [Security Guidelines](security.md)
- [Database Schema](database_schema.md)