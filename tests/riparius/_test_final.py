import pytest
from types import SimpleNamespace

from riparius.workflow import Workflow, Step, Stage, Role, transition, ALL_STATES
from riparius.status import WorkflowStatus, StepStatus
from riparius.exceptions import WorkflowExecutionError, WorkflowConfigurationError
from riparius.datadef import WorkflowState, WorkflowStep, validate_labels
from riparius.router import st_connect, wf_connect, EventRouter
from riparius.manager import WorkflowManager
from fluvius.data import UUID_GENF


class TestRipariusWorkflowSystem:
    """Test suite for the riparius workflow management system"""

    def setup_method(self):
        """Set up test fixtures"""
        # Clear registries before each test
        WorkflowManager.__registry__ = {}
        EventRouter.ROUTING_TABLE = {}

    def test_workflow_registration(self):
        """Test workflow registration with kebab-case keys"""
        class TestWorkflow(Workflow, title='Test Workflow', revision=1):
            stage = Stage('Test Stage')
            
            class TestStep(Step, title='Test Step', stage=stage):
                pass
                
        # Workflow keys are kebab-case
        assert 'test-workflow' in WorkflowManager.__registry__
        assert TestWorkflow.__title__ == 'Test Workflow'
        assert TestWorkflow.__revision__ == 1

    def test_step_state_machine(self):
        """Test step state machine with transitions"""
        stage = Stage('State Stage')
        
        class StateStep(Step, title='State Step', stage=stage):
            __states__ = ('CREATED', 'PROCESSING', 'COMPLETED', 'FAILED')
            __start__ = 'CREATED'
            
            @transition('PROCESSING', allowed_states=('CREATED',))
            def start_processing(self):
                return {'message': 'Started'}
                
            @transition('COMPLETED', allowed_states=('PROCESSING',))
            def complete_processing(self):
                return {'message': 'Completed'}
                
        assert StateStep.__states__ == ('CREATED', 'PROCESSING', 'COMPLETED', 'FAILED')
        assert StateStep.__start__ == 'CREATED'
        assert len(StateStep.__transitions__) == 2

    def test_event_routing(self):
        """Test event routing registration"""
        class EventWorkflow(Workflow, title='Event Workflow', revision=1):
            stage = Stage('Event Stage')
            
            @wf_connect('workflow-event')
            def handle_workflow_event(wf_state, event):
                yield f"Workflow handled: {event.data}"
                
            class EventStep(Step, title='Event Step', stage=stage):
                @st_connect('step-event')
                def handle_step_event(step_state, event):
                    yield f"Step handled: {event.data}"
                    
        assert 'workflow-event' in EventRouter.ROUTING_TABLE
        assert 'step-event' in EventRouter.ROUTING_TABLE

    def test_data_structures(self):
        """Test data structure creation and immutability"""
        wf_state = WorkflowState(
            state='test_state',
            label='TEST_LABEL',
            status=WorkflowStatus.ACTIVE
        )
        
        assert wf_state.state == 'test_state'
        assert wf_state.status == WorkflowStatus.ACTIVE
        
        # Test immutability
        updated = wf_state.set(status=WorkflowStatus.COMPLETED)
        assert wf_state.status == WorkflowStatus.ACTIVE
        assert updated.status == WorkflowStatus.COMPLETED

    def test_label_validation(self):
        """Test label validation"""
        result = validate_labels('CREATED', 'PROCESSING', 'COMPLETED')
        assert result == ('CREATED', 'PROCESSING', 'COMPLETED')
        
        with pytest.raises(ValueError):
            validate_labels('invalid_label')

    def test_status_categories(self):
        """Test status categorization"""
        assert WorkflowStatus.ACTIVE in WorkflowStatus._ACTIVE
        assert WorkflowStatus.BLANK in WorkflowStatus._INACTIVE
        assert WorkflowStatus.COMPLETED in WorkflowStatus._FINISHED
        
        assert StepStatus.COMPLETED in StepStatus._FINISHED
        assert StepStatus.ACTIVE not in StepStatus._FINISHED

    def test_workflow_validation_errors(self):
        """Test workflow configuration validation"""
        stage = Stage('Validation Stage')
        
        # Test transition to non-existent state
        with pytest.raises(WorkflowConfigurationError):
            class InvalidStep(Step, title='Invalid Step', stage=stage):
                @transition('NONEXISTENT')
                def invalid_transition(self):
                    pass

    def test_manager_functionality(self):
        """Test WorkflowManager basic functionality"""
        class ManagerWorkflow(Workflow, title='Manager Workflow', revision=1):
            stage = Stage('Manager Stage')
            
            class ManagerStep(Step, title='Manager Step', stage=stage):
                pass
                
        manager = WorkflowManager()
        assert 'manager-workflow' in WorkflowManager.__registry__
        assert hasattr(manager, 'process_event')

    def test_role_and_stage_definitions(self):
        """Test role and stage components"""
        stage = Stage('Test Stage', order=1)
        role = Role('Test Role')
        
        assert stage.__title__ == 'Test Stage'
        assert stage.__order__ == 1
        assert role.__title__ == 'Test Role'

    def test_multi_instance_steps(self):
        """Test multi-instance step configuration"""
        stage = Stage('Multi Stage')
        
        class SingleStep(Step, title='Single Step', stage=stage):
            pass
            
        class MultiStep(Step, title='Multi Step', stage=stage, multi=True):
            pass
            
        assert SingleStep.__multi__ == False
        assert MultiStep.__multi__ == True

    def test_all_states_transition(self):
        """Test transitions allowed from all states"""
        stage = Stage('Emergency Stage')
        
        class EmergencyStep(Step, title='Emergency Step', stage=stage):
            __states__ = ('CREATED', 'PROCESSING', 'EMERGENCY')
            
            @transition('EMERGENCY', allowed_states=(ALL_STATES,))
            def emergency_stop(self):
                return {'message': 'Emergency'}
                
        allowed_states, _ = EmergencyStep.__transitions__['EMERGENCY']
        assert allowed_states == (ALL_STATES,)

    def test_comprehensive_workflow(self):
        """Test a complete workflow scenario"""
        class CompleteWorkflow(Workflow, title='Complete Workflow', revision=1):
            init_stage = Stage('Initialization', order=1)
            proc_stage = Stage('Processing', order=2)
            
            admin_role = Role('Administrator')
            
            @wf_connect('workflow-start')
            def handle_start(wf_state, event):
                yield f"Started: {event.data}"
                
            class InitStep(Step, title='Init Step', stage=init_stage):
                __states__ = ('CREATED', 'INITIALIZING', 'COMPLETED')
                
                @st_connect('init-event')
                def handle_init(step_state, event):
                    yield f"Init: {event.data}"
                    
                @transition('INITIALIZING')
                def start_init(self):
                    return {'message': 'Started'}
                    
                @transition('COMPLETED', allowed_states=('INITIALIZING',))
                def complete_init(self):
                    return {'message': 'Completed'}
                    
            class ProcessStep(Step, title='Process Step', stage=proc_stage, multi=True):
                pass
                
        # Verify registration and configuration
        assert 'complete-workflow' in WorkflowManager.__registry__
        assert CompleteWorkflow.__title__ == 'Complete Workflow'
        assert CompleteWorkflow.InitStep.__states__ == ('CREATED', 'INITIALIZING', 'COMPLETED')
        assert CompleteWorkflow.ProcessStep.__multi__ == True
        
        # Verify event registration
        assert 'workflow-start' in EventRouter.ROUTING_TABLE
        assert 'init-event' in EventRouter.ROUTING_TABLE
        
        # Verify transitions
        assert len(CompleteWorkflow.InitStep.__transitions__) == 2 