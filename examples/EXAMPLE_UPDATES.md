# Example Domain Updates - Migration to Modern Library Patterns

This document describes the updates made to the `user_domain` and `banking_domain` examples to match the current fluvius library patterns.

## 🔄 **What Was Updated**

### **1. Command Structure Modernization**

#### **Before (Old Pattern):**
```python
@UserDomain.entity
class ActivateUser(UserCommand):
    pass

@UserDomain.command_processor(ActivateUser)
async def handle__activate_user(aggproxy, cmd):
    # Handler function separate from command
```

#### **After (Modern Pattern):**
```python
class ActivateUser(Command):
    class Meta:
        key = 'activate-user'
        name = 'Activate User'
        resources = ("app-user",)
        tags = ["user", "activation"]
        auth_required = True
        description = "Activate user account and set required actions"

    class Data(DataModel):
        pass

    async def _process(self, agg, stm, payload):
        # Inline processing method
```

### **2. Data Model Conversion**

#### **Before (Old Pattern):**
```python
from fluvius.domain.record import field
from fluvius.domain.command import CommandData

class DepositMoneyData(CommandData):
    amount = field(type=int, mandatory=True)
```

#### **After (Modern Pattern):**
```python
from fluvius.data import DataModel

class Data(DataModel):
    amount: int
    
    class Config:
        schema_extra = {
            "examples": [{"amount": 100}],
            "description": "Amount of money to deposit"
        }
```

### **3. Import Updates**

#### **Before:**
```python
from fluvius.domain.record import field
from fluvius.domain.command import Command, CommandData
from fluvius.domain.event import EventData
```

#### **After:**
```python
from fluvius.data import serialize_mapping, DataModel, UUID_TYPE
from fluvius.domain.aggregate import Aggregate
```

## 📋 **Updated Files**

### **User Domain (`examples/user_domain/`)**

#### **✅ `command.py`**
- **Converted 5 commands** to modern structure:
  - `ActivateUser`, `ExecuteUserAction`, `RemoveTOTP`, `DeactivateUser`, `ReconcileUser`
- **Added inline `_process` methods** for each command
- **Replaced field-based data** with `DataModel` classes
- **Added proper Meta configuration** with keys, names, resources, tags

#### **✅ `aggregate.py`**  
- **Updated base class** from `ObjectAggregate` to `Aggregate`
- **Modernized aggregate methods** to use state manager
- **Added proper event creation** with structured data
- **Added new method** `do__remove_totp`

#### **✅ `datadef.py` (New)**
- **Created modern data models** using `DataModel`
- **Added event data structures** for all user operations
- **Proper type annotations** and optional fields

#### **✅ `__init__.py`**
- **Updated imports** to include new modules
- **Added proper `__all__` exports**

### **Banking Domain (`examples/banking_domain/`)**

#### **✅ `command.py`**
- **Converted 3 commands** to modern structure:
  - `WithdrawMoney`, `DepositMoney`, `TransferMoney`
- **Inline data models** using `Command.Data = DataModel`
- **Added comprehensive Meta configuration**
- **Improved error handling** and response generation

#### **✅ `aggregate.py`**
- **Enhanced business logic** with proper validation
- **Updated to use state manager** for data persistence
- **Structured event data** with proper models
- **Added comprehensive error messages**

#### **✅ `datadef.py`**
- **Completely rewritten** to use `DataModel`
- **Added new data models**: `BankAccountData`, `TransactionHistoryData`
- **Removed old field-based patterns**
- **Added proper type annotations**

#### **✅ `__init__.py`**
- **Updated exports** to include new modules

## 🎯 **Key Improvements**

### **1. Modern Architecture**
- **Consistent patterns** with rfx-base examples
- **Inline command processing** instead of separate processors
- **Structured meta configuration** for better API generation
- **Type-safe data models** with Pydantic

### **2. Better Developer Experience**
- **Clear command structure** with descriptive meta information
- **Proper error handling** with meaningful messages
- **Comprehensive data validation** through DataModel
- **Consistent import patterns**

### **3. Enhanced Functionality**
- **Better state management** using statemgr
- **Structured event data** for better event handling
- **Comprehensive business logic** validation
- **Modern response patterns**

## 🧪 **Verification**

All examples can be imported successfully:

```python
import examples.user_domain.command as user_cmd
import examples.banking_domain.command as bank_cmd
import examples.banking_domain.datadef as bank_data
import examples.user_domain.aggregate as user_agg
import examples.banking_domain.aggregate as bank_agg
```

## 🚀 **Usage**

### **User Domain Commands:**
```python
# Activate user
ActivateUser(user_id="123")

# Execute actions
ExecuteUserAction(user_id="123", actions=["VERIFY_EMAIL"])

# Remove TOTP
RemoveTOTP(user_id="123")
```

### **Banking Domain Commands:**
```python
# Deposit money
DepositMoney(account_id="456", amount=100)

# Withdraw money  
WithdrawMoney(account_id="456", amount=50)

# Transfer money
TransferMoney(
    account_id="456",
    recipient="789",
    amount=25
)
```

## 📚 **Migration Benefits**

1. **🔧 Consistency**: All examples now follow the same modern patterns
2. **📖 Maintainability**: Easier to understand and maintain code structure
3. **🔒 Type Safety**: Better type checking with Pydantic models
4. **⚡ Performance**: More efficient with modern library optimizations
5. **🛠️ Tooling**: Better IDE support and API generation

**The example domains are now fully updated and ready for modern fluvius development!** 🎉 