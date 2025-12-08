# Docker Environment Configuration

The Workflow Manager Docker setup now uses environment variables stored in `.env` files for better configuration management.

## 🏗️ **Environment File Structure**

```
dkc/
├── docker-compose.yml    # Docker services configuration
├── .env                  # Environment variables (gitignored)
└── .env.example         # Template for environment variables
```

## 🔧 **Environment Variables**

### **Application Settings**
- `DATABASE_URL` - PostgreSQL connection string for the app
- `DEBUG` - Enable/disable debug mode
- `AUTH_ENABLED` - Enable/disable authentication

### **Database Settings**
- `POSTGRES_DB` - Database name
- `POSTGRES_USER` - Database user
- `POSTGRES_PASSWORD` - Database password

## 🚀 **Quick Setup**

### **1. Create Environment File**
```bash
# Copy template to create your .env file
cp dkc/.env.example dkc/.env

# Or use the automated setup
just docker-setup
```

### **2. Customize Environment (Optional)**
Edit `dkc/.env` to customize settings:
```bash
# Example customizations
DATABASE_URL=postgresql+asyncpg://myuser:mypass@db:5432/mydb
DEBUG=false
AUTH_ENABLED=true
POSTGRES_PASSWORD=secure_password_here
```

### **3. Start Services**
```bash
# Start with environment variables
just docker-compose-up

# Or with automatic setup
just docker-setup
```

## 📋 **Available Commands**

### **Docker Compose Commands**
```bash
just docker-setup         # Setup .env and start services
just docker-compose-up    # Start services
just docker-compose-down  # Stop services
just docker-build         # Build application image
```

### **Development Commands**
```bash
just dev-setup            # Setup local development
just dev                  # Run locally with auto-reload
```

## 🔒 **Security Notes**

### **Environment File Management**
- ✅ `.env.example` - Committed to git (template)
- ❌ `.env` - Gitignored (contains actual values)
- 🔧 Customize `.env` for your environment

### **Production Considerations**
- Use strong passwords in production
- Set `DEBUG=false` for production
- Enable authentication with `AUTH_ENABLED=true`
- Use secure database credentials

## 🔄 **Environment File Template**

```env
# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/workflow_manager
DEBUG=true
AUTH_ENABLED=false

# PostgreSQL Database Settings
POSTGRES_DB=workflow_manager
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
```

## 🛠️ **Troubleshooting**

### **Missing .env File**
```bash
# If .env is missing, copy from template
cp dkc/.env.example dkc/.env
```

### **Permission Issues**
```bash
# Fix file permissions if needed
chmod 644 dkc/.env
```

### **Variable Not Loading**
```bash
# Test that variables are being read
cd dkc && docker-compose config
```

## 🎯 **Benefits**

1. **🔧 Easy Configuration**: Simple environment variable management
2. **🔒 Security**: Sensitive values not committed to git
3. **🌍 Environment Specific**: Different settings for dev/prod
4. **📝 Self-Documenting**: Clear template shows required variables
5. **🚀 Quick Setup**: Automated environment setup commands

The Docker environment is now properly configured with external environment variables for flexible and secure deployment! 🎉 