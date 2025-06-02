import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite
from sqlalchemy.ext.declarative import declarative_base
import re

from fluvius.data.data_driver import SqlaDriver
# from fluvius.data.data_driver.sqla.query import QueryBuilder # Not strictly needed for these tests
# from fluvius.data.data_schema import SqlaDataSchema # Original, for reference
from fluvius.data.query import BackendQuery, JoinStatement

# --- SQL Comparison Helper ---
def normalize_sql(sql: str) -> str:
    # Remove excessive whitespace, newlines, and normalize case for comparison
    sql = re.sub(r"\s+", " ", sql)
    return sql.strip().lower()

def assert_sql_equivalent(actual: str, expected: str):
    assert normalize_sql(actual) == normalize_sql(expected), f"\nExpected SQL:\n{expected}\n\nActual SQL:\n{actual}\n"

# --- Test SqlaDriver (customized for local schemas) ---
class SqlaDriverForTesting(SqlaDriver):
    __db_dsn__ = "sqlite+aiosqlite:///:memory:" # In-memory for testing

    def compile_statement(self, stmt):
        return str(stmt.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}))

# --- Test Schemas (using local base) ---
BaseTestSchema = SqlaDriverForTesting.__data_schema_base__

class UserSchema(BaseTestSchema):
    __tablename__ = 'user'
    _id = sa.Column(sa.String, primary_key=True)
    name = sa.Column(sa.String)
    age = sa.Column(sa.Integer)
    email = sa.Column(sa.String)
    is_active = sa.Column(sa.Boolean, default=True)
    created_at = sa.Column(sa.DateTime, default=sa.func.now())

class CompanySchema(BaseTestSchema):
    __tablename__ = 'company'
    _id = sa.Column(sa.String, primary_key=True)
    name = sa.Column(sa.String)
    industry = sa.Column(sa.String)
    employee_count = sa.Column(sa.Integer)

class DepartmentSchema(BaseTestSchema):
    __tablename__ = 'department'
    _id = sa.Column(sa.String, primary_key=True)
    name = sa.Column(sa.String)
    company_id = sa.Column(sa.String, sa.ForeignKey('company._id'))




@pytest.fixture(scope="module")
def test_driver():
    driver = SqlaDriverForTesting()
    # Create tables for this specific metadata if needed for any execution tests (not just compilation)
    # LocalTestFileBase.metadata.create_all(driver._async_session._async_engine) # Requires async setup
    return driver

# --- Test Cases ---

def test_build_select_simple(test_driver):
    query = BackendQuery.create()
    stmt = test_driver.build_select(UserSchema, query)
    expected_sql = '''
        SELECT user._id, user.name, user.age, user.email, user.is_active, user.created_at
        FROM user
        LIMIT 100 OFFSET 0
    '''
    assert_sql_equivalent(test_driver.compile_statement(stmt), expected_sql)

def test_build_select_with_specific_fields(test_driver):
    query = BackendQuery.create(select=['_id', 'name', 'email'])
    stmt = test_driver.build_select(UserSchema, query)
    expected_sql = '''
        SELECT user._id, user.name, user.email
        FROM user
        LIMIT 100 OFFSET 0
    '''
    assert_sql_equivalent(test_driver.compile_statement(stmt), expected_sql)

def test_build_select_with_identifier(test_driver):
    user_id = "user-123"
    query = BackendQuery.create(identifier=user_id)
    stmt = test_driver.build_select(UserSchema, query)
    expected_sql = f'''
        SELECT user._id, user.name, user.age, user.email, user.is_active, user.created_at
        FROM user
        WHERE user._id = '{user_id}'
        LIMIT 100 OFFSET 0
    '''
    assert_sql_equivalent(test_driver.compile_statement(stmt), expected_sql)

def test_build_select_with_where_eq(test_driver):
    query = BackendQuery.create(where={"name": "John Doe"})
    stmt = test_driver.build_select(UserSchema, query)
    expected_sql = '''
        SELECT user._id, user.name, user.age, user.email, user.is_active, user.created_at
        FROM user
        WHERE user.name = 'John Doe'
        LIMIT 100 OFFSET 0
    '''
    assert_sql_equivalent(test_driver.compile_statement(stmt), expected_sql)

def test_build_select_with_where_ne(test_driver):
    query = BackendQuery.create(where={"name:ne": "John Doe"})
    stmt = test_driver.build_select(UserSchema, query)
    expected_sql = '''
        SELECT user._id, user.name, user.age, user.email, user.is_active, user.created_at
        FROM user
        WHERE user.name != 'John Doe'
        LIMIT 100 OFFSET 0
    '''
    assert_sql_equivalent(test_driver.compile_statement(stmt), expected_sql)
    
def test_build_select_with_where_negated_eq(test_driver):
    query = BackendQuery.create(where={"name!eq": "John Doe"})
    stmt = test_driver.build_select(UserSchema, query)
    expected_sql = '''
        SELECT user._id, user.name, user.age, user.email, user.is_active, user.created_at
        FROM user
        WHERE user.name != 'John Doe'
        LIMIT 100 OFFSET 0
    '''
    assert_sql_equivalent(test_driver.compile_statement(stmt), expected_sql)

def test_build_select_with_where_gt_lt_gte_lte(test_driver):
    query = BackendQuery.create(where={":and": [{"age:gt": 30}, {"age:lte": 40}]})
    stmt = test_driver.build_select(UserSchema, query)
    expected_sql = '''
        SELECT user._id, user.name, user.age, user.email, user.is_active, user.created_at
        FROM user
        WHERE user.age > 30 AND user.age <= 40
        LIMIT 100 OFFSET 0
    '''
    assert_sql_equivalent(test_driver.compile_statement(stmt), expected_sql)

def test_build_select_with_where_in_notin(test_driver):
    names = ["Alice", "Bob"]
    query_in = BackendQuery.create(where={"name:in": names})
    stmt_in = test_driver.build_select(UserSchema, query_in)
    expected_sql_in = '''
        SELECT user._id, user.name, user.age, user.email, user.is_active, user.created_at
        FROM user
        WHERE user.name IN ('Alice', 'Bob')
        LIMIT 100 OFFSET 0
    '''
    actual_sql_in = test_driver.compile_statement(stmt_in)
    assert "user.name IN" in actual_sql_in
    assert "LIMIT 100 OFFSET 0" in actual_sql_in

    query_notin = BackendQuery.create(where={"name:notin": names})
    stmt_notin = test_driver.build_select(UserSchema, query_notin)
    expected_sql_notin = '''
        SELECT user._id, user.name, user.age, user.email, user.is_active, user.created_at
        FROM user
        WHERE (user.name NOT IN ('Alice', 'Bob'))
        LIMIT 100 OFFSET 0
    '''
    actual_sql_notin = test_driver.compile_statement(stmt_notin)
    assert "user.name NOT IN" in actual_sql_notin
    assert "LIMIT 100 OFFSET 0" in actual_sql_notin
    
    query_negated_in = BackendQuery.create(where={"name!in": names}) # !in is equivalent to :notin
    stmt_negated_in = test_driver.build_select(UserSchema, query_negated_in)
    actual_sql_negated_in = test_driver.compile_statement(stmt_negated_in)
    assert "user.name NOT IN" in actual_sql_negated_in

def test_build_select_with_where_cs_ilike(test_driver):
    query_cs = BackendQuery.create(where={"name:cs": "%John%"})
    stmt_cs = test_driver.build_select(UserSchema, query_cs)
    actual_sql_cs = test_driver.compile_statement(stmt_cs)
    assert "user.name LIKE" in actual_sql_cs
    assert "LIMIT 100 OFFSET 0" in actual_sql_cs

    query_ilike = BackendQuery.create(where={"name:ilike": "%john%"})
    stmt_ilike = test_driver.build_select(UserSchema, query_ilike)
    actual_sql_ilike = test_driver.compile_statement(stmt_ilike)
    assert "lower(" in actual_sql_ilike or "ILIKE" in actual_sql_ilike or "user.name LIKE" in actual_sql_ilike
    assert "LIMIT 100 OFFSET 0" in actual_sql_ilike

def test_build_select_with_where_and_or(test_driver):
    query_and = BackendQuery.create(where={":and": [{"name": "John"}, {"age:gt": 25}]})
    stmt_and = test_driver.build_select(UserSchema, query_and)
    expected_sql_and = '''
        SELECT user._id, user.name, user.age, user.email, user.is_active, user.created_at
        FROM user
        WHERE user.name = 'John' AND user.age > 25
        LIMIT 100 OFFSET 0
    '''
    assert_sql_equivalent(test_driver.compile_statement(stmt_and), expected_sql_and)

    query_or = BackendQuery.create(where={":or": [{"name": "Jane"}, {"age:lt": 20}]})
    stmt_or = test_driver.build_select(UserSchema, query_or)
    expected_sql_or = '''
        SELECT user._id, user.name, user.age, user.email, user.is_active, user.created_at
        FROM user
        WHERE user.name = 'Jane' OR user.age < 20
        LIMIT 100 OFFSET 0
    '''
    assert_sql_equivalent(test_driver.compile_statement(stmt_or), expected_sql_or)

def test_build_select_with_where_negated_and_or(test_driver):
    query_nand = BackendQuery.create(where={"!and": [{"name": "John"}, {"age:gt": 25}]})
    stmt_nand = test_driver.build_select(UserSchema, query_nand)
    expected_sql_nand = '''
        SELECT user._id, user.name, user.age, user.email, user.is_active, user.created_at
        FROM user
        WHERE NOT (user.name = 'John' AND user.age > 25)
        LIMIT 100 OFFSET 0
    '''
    assert_sql_equivalent(test_driver.compile_statement(stmt_nand), expected_sql_nand)

    query_nor = BackendQuery.create(where={"!or": [{"name": "Jane"}, {"age:lt": 20}]})
    stmt_nor = test_driver.build_select(UserSchema, query_nor)
    expected_sql_nor = '''
        SELECT user._id, user.name, user.age, user.email, user.is_active, user.created_at
        FROM user
        WHERE NOT (user.name = 'Jane' OR user.age < 20)
        LIMIT 100 OFFSET 0
    '''
    assert_sql_equivalent(test_driver.compile_statement(stmt_nor), expected_sql_nor)
    
def test_build_select_with_limit_offset(test_driver):
    query = BackendQuery.create(limit=10, offset=5)
    stmt = test_driver.build_select(UserSchema, query)
    expected_sql = '''
        SELECT user._id, user.name, user.age, user.email, user.is_active, user.created_at
        FROM user
        LIMIT 10 OFFSET 5
    '''
    assert_sql_equivalent(test_driver.compile_statement(stmt), expected_sql)

def test_build_select_with_sort(test_driver):
    query_asc = BackendQuery.create(sort=['name']) # Default asc
    stmt_asc = test_driver.build_select(UserSchema, query_asc)
    expected_sql_asc = '''
        SELECT user._id, user.name, user.age, user.email, user.is_active, user.created_at
        FROM user
        ORDER BY user.name ASC
        LIMIT 100 OFFSET 0
    '''
    assert_sql_equivalent(test_driver.compile_statement(stmt_asc), expected_sql_asc)
    
    query_desc = BackendQuery.create(sort=['name:desc'])
    stmt_desc = test_driver.build_select(UserSchema, query_desc)
    expected_sql_desc = '''
        SELECT user._id, user.name, user.age, user.email, user.is_active, user.created_at
        FROM user
        ORDER BY user.name DESC
        LIMIT 100 OFFSET 0
    '''
    assert_sql_equivalent(test_driver.compile_statement(stmt_desc), expected_sql_desc)

    query_multi_sort = BackendQuery.create(sort=['age:desc', 'name:asc'])
    stmt_multi_sort = test_driver.build_select(UserSchema, query_multi_sort)
    expected_sql_multi_sort = '''
        SELECT user._id, user.name, user.age, user.email, user.is_active, user.created_at
        FROM user
        ORDER BY user.age DESC, user.name ASC
        LIMIT 100 OFFSET 0
    '''
    assert_sql_equivalent(test_driver.compile_statement(stmt_multi_sort), expected_sql_multi_sort)

def test_build_select_with_join(test_driver):
    query_for_join = BackendQuery.create(
        select=['_id', 'name', 'department.name'], # Company._id, Company.name, Department.name
        join=[
            JoinStatement(
                local_field='_id',
                foreign_table='department',
                foreign_field='company_id'
            )
        ],
        where={"industry": "Tech"}
    )
    stmt = test_driver.build_select(CompanySchema, query_for_join)
    # SQLAlchemy may generate different alias names, so check for key components
    actual_sql = test_driver.compile_statement(stmt)
    assert "company._id" in actual_sql
    assert "company.name" in actual_sql  
    assert "department.name AS" in actual_sql  # SQLAlchemy will alias this field
    assert "FROM company JOIN department" in actual_sql
    assert "company._id = department.company_id" in actual_sql
    assert "company.industry = 'Tech'" in actual_sql
    assert "LIMIT 100 OFFSET 0" in actual_sql


def test_build_select_with_scope(test_driver):
    query = BackendQuery.create(scope={"is_active": True})
    stmt = test_driver.build_select(UserSchema, query)
    expected_sql = '''
        SELECT user._id, user.name, user.age, user.email, user.is_active, user.created_at
        FROM user
        WHERE user.is_active = 1
        LIMIT 100 OFFSET 0
    '''
    assert_sql_equivalent(test_driver.compile_statement(stmt), expected_sql)

def test_build_select_with_field_mapping(test_driver):
    query = BackendQuery.create(
        select=['user_name', 'user_age'],
        mapping={"user_name": "name", "user_age": "age"},
        where={"user_name": "Mapped Name"}
    )
    stmt = test_driver.build_select(UserSchema, query)
    # Aliases in select are user_name, user_age. These are simple and likely unquoted by SQLite.
    expected_sql = '''
        SELECT user.name AS user_name, user.age AS user_age
        FROM user
        WHERE user.name = 'Mapped Name'
        LIMIT 100 OFFSET 0
    '''
    assert_sql_equivalent(test_driver.compile_statement(stmt), expected_sql)
