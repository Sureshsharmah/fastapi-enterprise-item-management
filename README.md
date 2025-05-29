# 📋 **FastAPI Item Management System - Assessment Project**

A comprehensive FastAPI application implementing progressive backend development stages with in-memory persistence, PostgreSQL integration, and advanced data management features.

## 🎯 **Project Overview**

This project demonstrates a complete backend solution built in three progressive stages:

- **Stage 1**: FastAPI application with in-memory persistence and file-based backup
- **Stage 2**: PostgreSQL database integration with stored procedures
- **Stage 3**: Duplicate prevention and crash recovery mechanisms


## 🏗️ **Architecture & Features**

### **Core Features**

- ✅ RESTful API with FastAPI framework
- ✅ Dual persistence (in-memory + PostgreSQL)
- ✅ Automatic crash recovery with file-based backup
- ✅ Duplicate prevention at application and database levels
- ✅ Comprehensive error handling and validation
- ✅ Thread-safe operations with proper locking
- ✅ Health monitoring and logging
- ✅ CORS configuration for cross-origin requests


### **API Endpoints**

| Endpoint | Method | Description
|-----|-----|-----
| `/add` | POST | Add new item with duplicate prevention
| `/snapshot` | POST | Retrieve items sorted by specified field
| `/remove` | POST | Remove item by ID
| `/clear` | POST | Clear all items
| `/health` | GET | Health check and system status


## 🚀 **Quick Start**

### **Prerequisites**

- Python 3.8+
- PostgreSQL 12+
- Git


### **1. Clone Repository**

```shellscript
git clone https://github.com/Sureshsharmah/fastapi-enterprise-item-management
cd fastapi-assessment
```

### **2. Setup Virtual Environment**

```shellscript
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate

### **3. Install Dependencies**

```shellscript
pip install -r requirements.txt
```

### **4. Configure Environment**

Create a `.env` file in the project root:

```plaintext
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASS=Suresh@123
DB_NAME=developer
```

### **5. Setup Database**

```shellscript
# Connect to PostgreSQL and run the setup script
psql -U postgres -d developer -f database_setup.sql
```

### **6. Run Application**

```shellscript
uvicorn app:app --reload
```

### **7. Access API Documentation**

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
