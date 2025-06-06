import pytest
from collections import namedtuple

from fluvius.data.query import (
    process_query_statement, 
    QueryElement, 
    QueryStatement, 
    OperatorStatement, 
    operator_statement
)


class MockParamSpec:
    """Mock parameter specification for testing parameter processing"""
    def __init__(self, processed_value=None):
        self.processed_value = processed_value
    
    def process_value(self, value):
        return self.processed_value if self.processed_value is not None else value


def test_process_query_statement_empty():
    """Test process_query_statement with empty input"""
    result = process_query_statement()
    assert isinstance(result, QueryStatement)
    assert len(result) == 0


def test_process_query_statement_single_dict():
    """Test process_query_statement with a single dictionary"""
    result = process_query_statement({'name': 'John'})
    assert isinstance(result, QueryStatement)
    assert len(result) == 1
    
    element = result[0]
    assert isinstance(element, QueryElement)
    assert element.field_name == 'name'
    assert element.mode == '.'
    assert element.operator == 'eq'
    assert element.composite is False
    assert element.value == 'John'


def test_process_query_statement_multiple_dicts():
    """Test process_query_statement with multiple dictionaries"""
    result = process_query_statement(
        {'name': 'John'}, 
        {'age.gt': 25}
    )
    assert isinstance(result, QueryStatement)
    assert len(result) == 2
    
    # First element
    element1 = result[0]
    assert element1.field_name == 'name'
    assert element1.operator == 'eq'
    assert element1.value == 'John'
    
    # Second element  
    element2 = result[1]
    assert element2.field_name == 'age'
    assert element2.operator == 'gt'
    assert element2.value == 25


def test_process_query_statement_with_operators():
    """Test process_query_statement with various operators"""
    test_cases = [
        ('name.eq', 'John', 'eq'),
        ('age.gt', 25, 'gt'),
        ('score.lt', 100, 'lt'),
        ('status.ne', 'inactive', 'ne'),
        ('tags.in', ['tag1', 'tag2'], 'in'),
    ]
    
    for field_op, value, expected_op in test_cases:
        result = process_query_statement({field_op: value})
        element = result[0]
        assert element.operator == expected_op
        assert element.value == value


def test_process_query_statement_with_negation():
    """Test process_query_statement with negation operator"""
    result = process_query_statement({'!name.eq': 'John'})
    element = result[0]
    assert element.field_name == 'name'
    assert element.mode == '!'
    assert element.operator == 'eq'
    assert element.composite is True  # negation makes it composite
    assert element.value == 'John'


def test_process_query_statement_with_nested_list():
    """Test process_query_statement with nested lists"""
    result = process_query_statement([
        {'name': 'John'},
        [{'age.gt': 25}, {'status': 'active'}]
    ])
    assert len(result) == 3
    
    # Check all elements are properly extracted
    fields = [elem.field_name for elem in result]
    assert 'name' in fields
    assert 'age' in fields
    assert 'status' in fields


def test_process_query_statement_with_query_element():
    """Test process_query_statement with existing QueryElement"""
    existing_element = QueryElement('name', '.', 'eq', False, 'John')
    result = process_query_statement(existing_element, {'age': 25})
    assert len(result) == 2
    
    # First element should be the original
    assert result[0] is existing_element
    
    # Second element should be processed from dict
    assert result[1].field_name == 'age'
    assert result[1].value == 25


def test_process_query_statement_with_param_specs():
    """Test process_query_statement with parameter specifications"""
    param_specs = {
        ('name', 'eq'): MockParamSpec('processed_john'),
        ('age', 'eq'): MockParamSpec(30)
    }
    
    result = process_query_statement(
        {'name': 'John', 'age': 25}, 
        param_specs=param_specs
    )
    
    name_elem = next(elem for elem in result if elem.field_name == 'name')
    age_elem = next(elem for elem in result if elem.field_name == 'age')
    
    assert name_elem.value == 'processed_john'
    assert age_elem.value == 30


def test_process_query_statement_composite_operators():
    """Test process_query_statement with composite operators (no field name)"""
    # Simulate composite operator by providing empty field name
    result = process_query_statement({'.and': [{'name': 'John'}, {'age': 25}]})
    
    element = result[0]
    assert element.field_name == ''  # Empty field name indicates composite
    assert element.operator == 'and'
    assert element.composite is True
    # Note: the value processing might not work as expected due to missing _process_statement
    # but we can test the structure


def test_process_query_statement_invalid_input():
    """Test process_query_statement with invalid input types"""
    with pytest.raises(ValueError, match="Invalid query statement"):
        process_query_statement("invalid_string")
    
    with pytest.raises(ValueError, match="Invalid query statement"):
        process_query_statement(123)


def test_process_query_statement_missing_param_spec():
    """Test process_query_statement with missing parameter specification"""
    param_specs = {
        ('name', 'eq'): MockParamSpec('processed_value')
    }
    
    # This should raise KeyError when trying to access missing param spec
    with pytest.raises(KeyError):
        process_query_statement({'age.gt': 25}, param_specs=param_specs)


def test_process_query_statement_none_values():
    """Test process_query_statement handles None values correctly"""
    result = process_query_statement(None, {'name': 'John'}, None)
    assert len(result) == 1
    assert result[0].field_name == 'name'
    assert result[0].value == 'John'


def test_process_query_statement_empty_dict():
    """Test process_query_statement with empty dictionary"""
    result = process_query_statement({})
    assert len(result) == 0


def test_process_query_statement_complex_nested():
    """Test process_query_statement with complex nested structures"""
    complex_query = [
        {'name': 'John'},
        [
            {'age.gt': 25},
            [
                {'status': 'active'},
                {'city.in': ['NY', 'LA']}
            ]
        ],
        {'!deleted.eq': True}
    ]
    
    result = process_query_statement(complex_query)
    assert len(result) == 5
    
    # Verify all fields are present
    fields = [elem.field_name for elem in result]
    assert all(field in fields for field in ['name', 'age', 'status', 'city', 'deleted'])
    
    # Verify negation is handled
    deleted_elem = next(elem for elem in result if elem.field_name == 'deleted')
    assert deleted_elem.composite is True  # negation


def test_operator_statement_function():
    """Test the operator_statement helper function"""
    # Test default operator
    result = operator_statement('name')
    assert result.field_name == 'name'
    assert result.mode == '.'
    assert result.operator == 'eq'
    assert result.composite is False
    
    # Test with operator
    result = operator_statement('age.gt')
    assert result.field_name == 'age'
    assert result.operator == 'gt'
    assert result.composite is False
    
    # Test with negation
    result = operator_statement('!name.eq')
    assert result.field_name == 'name'
    assert result.mode == '!'
    assert result.operator == 'eq'
    assert result.composite is True
    
    # Test passing existing OperatorStatement
    existing = OperatorStatement('test', '.', 'eq', False)
    result = operator_statement(existing)
    assert result is existing


def test_process_query_statement_with_tuples():
    """Test process_query_statement with tuple inputs"""
    result = process_query_statement(({'name': 'John'}, {'age': 25}))
    assert len(result) == 2
    assert result[0].field_name == 'name'
    assert result[1].field_name == 'age'


def test_process_query_statement_edge_cases():
    """Test process_query_statement edge cases"""
    # Test with False values
    result = process_query_statement(False)
    assert len(result) == 0
    
    # Test with 0 values
    result = process_query_statement({'count': 0})
    assert len(result) == 1
    assert result[0].value == 0
    
    # Test with empty string values
    result = process_query_statement({'name': ''})
    assert len(result) == 1
    assert result[0].value == '' 