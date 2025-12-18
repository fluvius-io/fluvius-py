"""
Tests for DocumentTemplate to_json method
"""
import json
import pytest

from fluvius.dform.document import (
    DocumentTemplate,
    DocumentSection,
    ContentNode,
    FormNode,
)

# Import dform_app to ensure forms are registered
import fluvius_test.dform_app  # noqa: F401
from fluvius_test.dform_app import (
    LoanApplicationTemplate,
    CustomerOnboardingTemplate,
    TEMPLATES,
)


class TestDocumentTemplateToJson:
    """Tests for DocumentTemplate.to_json() method"""

    def test_simple_template_to_json(self):
        """Test to_json with a simple template"""
        template = DocumentTemplate(
            template_key="test-template",
            title="Test Template",
            children=[]
        )
        
        json_data = template.to_json()
        
        assert json_data["node_type"] == "DocumentTemplate"
        assert json_data["template_key"] == "test-template"
        assert json_data["title"] == "Test Template"
        assert json_data["children"] == []
        
        # Print JSON output
        print("\n=== Simple Template JSON ===")
        print(json.dumps(json_data, indent=2))

    def test_template_with_content_nodes(self):
        """Test to_json with content nodes"""
        template = DocumentTemplate(
            template_key="content-template",
            title="Content Template",
            children=[
                ContentNode(title="Header", content="Welcome!", ctype="header"),
                ContentNode(title="Intro", content="This is the intro.", ctype="text"),
            ]
        )
        
        json_data = template.to_json()
        
        assert json_data["node_type"] == "DocumentTemplate"
        assert len(json_data["children"]) == 2
        assert json_data["children"][0]["node_type"] == "ContentNode"
        assert json_data["children"][0]["ctype"] == "header"
        assert json_data["children"][0]["title"] == "Header"
        assert json_data["children"][1]["node_type"] == "ContentNode"
        assert json_data["children"][1]["ctype"] == "text"
        
        # Print JSON output
        print("\n=== Template with Content Nodes JSON ===")
        print(json.dumps(json_data, indent=2))

    def test_template_with_sections(self):
        """Test to_json with nested sections"""
        template = DocumentTemplate(
            template_key="section-template",
            title="Section Template",
            children=[
                DocumentSection(
                    title="Section 1",
                    children=[
                        ContentNode(title="Info", content="Section 1 content", ctype="text"),
                    ]
                ),
                DocumentSection(
                    title="Section 2",
                    children=[
                        ContentNode(title="Info", content="Section 2 content", ctype="text"),
                    ]
                ),
            ]
        )
        
        json_data = template.to_json()
        
        assert json_data["node_type"] == "DocumentTemplate"
        assert len(json_data["children"]) == 2
        assert json_data["children"][0]["node_type"] == "DocumentSection"
        assert json_data["children"][0]["title"] == "Section 1"
        assert json_data["children"][1]["node_type"] == "DocumentSection"
        assert json_data["children"][1]["title"] == "Section 2"
        assert len(json_data["children"][0]["children"]) == 1
        assert json_data["children"][0]["children"][0]["node_type"] == "ContentNode"
        
        # Print JSON output
        print("\n=== Template with Sections JSON ===")
        print(json.dumps(json_data, indent=2))

    def test_template_with_form_nodes(self):
        """Test to_json with form node references"""
        template = DocumentTemplate(
            template_key="form-template",
            title="Form Template",
            children=[
                DocumentSection(
                    title="Application Section",
                    children=[
                        FormNode(form_key="applicant-info"),
                        FormNode(form_key="employment-details", attrs={"header": "Custom Header"}),
                    ]
                ),
            ]
        )
        
        json_data = template.to_json()
        
        assert json_data["node_type"] == "DocumentTemplate"
        section = json_data["children"][0]
        assert section["node_type"] == "DocumentSection"
        assert len(section["children"]) == 2
        assert section["children"][0]["node_type"] == "FormNode"
        assert section["children"][0]["form_key"] == "applicant-info"
        assert section["children"][1]["node_type"] == "FormNode"
        assert section["children"][1]["form_key"] == "employment-details"
        assert section["children"][1]["attrs"]["header"] == "Custom Header"
        
        # Print JSON output
        print("\n=== Template with Form Nodes JSON ===")
        print(json.dumps(json_data, indent=2))

    def test_loan_application_template_to_json(self):
        """Test to_json with the full LoanApplicationTemplate"""
        json_data = LoanApplicationTemplate.to_json()
        
        assert json_data["node_type"] == "DocumentTemplate"
        assert json_data["template_key"] == "loan-application"
        assert json_data["title"] == "Loan Application Form"
        assert len(json_data["children"]) > 0
        
        # Check all children have node_type
        for child in json_data["children"]:
            assert "node_type" in child
        
        # Print JSON output
        print("\n=== Loan Application Template JSON ===")
        print(json.dumps(json_data, indent=2))

    def test_customer_onboarding_template_to_json(self):
        """Test to_json with CustomerOnboardingTemplate"""
        json_data = CustomerOnboardingTemplate.to_json()
        
        assert json_data["node_type"] == "DocumentTemplate"
        assert json_data["template_key"] == "customer-onboarding"
        assert json_data["title"] == "Customer Onboarding Form"
        
        # Print JSON output
        print("\n=== Customer Onboarding Template JSON ===")
        print(json.dumps(json_data, indent=2))

    def test_all_templates_to_json(self):
        """Test to_json for all templates in dform_app"""
        print("\n=== All Templates JSON Summary ===")
        
        for template in TEMPLATES:
            json_data = template.to_json()
            
            # Verify basic structure
            assert json_data["node_type"] == "DocumentTemplate"
            assert "template_key" in json_data
            assert "title" in json_data
            assert "children" in json_data
            
            # Verify JSON serializable
            json_str = json.dumps(json_data)
            assert isinstance(json_str, str)
            
            # Print summary
            sections = [c for c in json_data["children"] if c.get("node_type") == "DocumentSection"]
            print(f"\nTemplate: {json_data['template_key']}")
            print(f"  Title: {json_data['title']}")
            print(f"  Top-level children: {len(json_data['children'])}")
            print(f"  Sections: {len(sections)}")

    def test_to_json_is_serializable(self):
        """Test that to_json output is fully JSON serializable"""
        json_data = LoanApplicationTemplate.to_json()
        
        # Should not raise
        json_str = json.dumps(json_data)
        
        # Should round-trip
        parsed = json.loads(json_str)
        assert parsed == json_data
        
        print("\n=== JSON Serialization Test ===")
        print(f"Original keys: {list(json_data.keys())}")
        print(f"JSON string length: {len(json_str)} chars")
        print(f"Round-trip successful: True")

    def test_node_types_present(self):
        """Test that all node types are correctly identified in JSON"""
        template = DocumentTemplate(
            template_key="mixed-template",
            title="Mixed Template",
            children=[
                ContentNode(title="Header", content="Welcome", ctype="header"),
                DocumentSection(
                    title="Section",
                    children=[
                        ContentNode(title="Text", content="Some text", ctype="text"),
                        FormNode(form_key="applicant-info"),
                    ]
                ),
            ]
        )
        
        json_data = template.to_json()
        
        # Collect all node types
        node_types = set()
        
        def collect_types(data):
            if isinstance(data, dict):
                if "node_type" in data:
                    node_types.add(data["node_type"])
                for v in data.values():
                    collect_types(v)
            elif isinstance(data, list):
                for item in data:
                    collect_types(item)
        
        collect_types(json_data)
        
        assert "DocumentTemplate" in node_types
        assert "ContentNode" in node_types
        assert "DocumentSection" in node_types
        assert "FormNode" in node_types
        
        print("\n=== Node Types Found ===")
        print(f"Node types: {sorted(node_types)}")
        print(json.dumps(json_data, indent=2))
