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
    """Comprehensive test suite for the riparius workflow management system"""

    def setup_method(self):
        """Set up test fixtures"""
        # Clear registries before each test
        WorkflowManager.__registry__ = {}
        EventRouter.ROUTING_TABLE = {}

    def test_workflow_registration_and_key_generation(self):
        """Test workflow registration with automatic key generation"""
        class TestWorkflow(Workflow, title='Test Workflow', revision=1):
            stage = Stage('Test Stage')
            
            class TestStep(Step, title='Test Step', stage=stage):
                pass
                
        # Verify workflow is registered with kebab-case key
        assert 'test-workflow' in WorkflowManager.__registry__
        
        # Verify workflow metadata
        assert TestWorkflow.__title__ == 'Test Workflow'
        assert TestWorkflow.__revision__ == 1
        # The actual key is kebab-case, not snake_case
        assert TestWorkflow.__key__ == 'test-workflow'

    def test_custom_workflow_key(self):
        """Test workflow with custom key"""
        class CustomWorkflow(Workflow, title='Custom Workflow', revision=1):
            __key__ = 'my_custom_key'
            stage = Stage('Custom Stage')
            
            class CustomStep(Step, title='Custom Step', stage=stage):
                pass
                
        # Custom key should be preserved
        assert CustomWorkflow.__key__ == 'my_custom_key'
        assert 'my_custom_key' in WorkflowManager.__registry__

    def test_step_state_machine_configuration(self):
        """Test step state machine with transitions"""
        stage = Stage('State Stage')
        
        class StateMachineStep(Step, title='State Machine Step', stage=stage):
            __states__ = ('CREATED', 'PROCESSING', 'COMPLETED', 'FAILED')
            __start__ = 'CREATED'
            
            @transition('PROCESSING', allowed_states=('CREATED',))
            def start_processing(self):
                return {'message': 'Started'}
                
            @transition('COMPLETED', allowed_states=('PROCESSING',))
            def complete_processing(self):
                return {'message': 'Completed'}
                
            @transition('FAILED')  # Can transition from any state
            def fail_processing(self):
                return {'message': 'Failed'}
                
        # Verify state configuration
        assert StateMachineStep.__states__ == ('CREATED', 'PROCESSING', 'COMPLETED', 'FAILED')
        assert StateMachineStep.__start__ == 'CREATED'
        assert len(StateMachineStep.__transitions__) == 3
        
        # Verify specific transition rules
        allowed_states, _ = StateMachineStep.__transitions__['COMPLETED']
        assert allowed_states == ('PROCESSING',)

    def test_event_routing_registration(self):
        """Test event routing for workflows and steps"""
        class EventWorkflow(Workflow, title='Event Workflow', revision=1):
            stage = Stage('Event Stage')
            
            @wf_connect('workflow-event')
            def handle_workflow_event(wf_state, event):
                yield f"Workflow handled: {event.data}"
                
            class EventStep(Step, title='Event Step', stage=stage):
                @st_connect('step-event')
                def handle_step_event(step_state, event):
                    yield f"Step handled: {event.data}"
                    
        # Verify events are registered
        assert 'workflow-event' in EventRouter.ROUTING_TABLE
        assert 'step-event' in EventRouter.ROUTING_TABLE
        
        # Verify handler structure
        wf_handlers = EventRouter.ROUTING_TABLE['workflow-event']
        step_handlers = EventRouter.ROUTING_TABLE['step-event']
        
        assert len(wf_handlers) == 1
        assert len(step_handlers) == 1
        
        # Check handler properties (workflow key is kebab-case)
        wf_handler = wf_handlers[0]
        step_handler = step_handlers[0]
        
        assert wf_handler.workflow_key == 'event-workflow'
        assert wf_handler.step_key is None
        assert step_handler.workflow_key == 'event-workflow'
        assert step_handler.step_key == 'EventStep'

    def test_data_structures(self):
        """Test riparius data structures and immutability"""
        # Test WorkflowState creation
        wf_state = WorkflowState(
            state='test_state',
            label='TEST_LABEL',
            status=WorkflowStatus.ACTIVE,
            params={'param': 'value'},
            memory={'mem': 'data'}
        )
        
        assert wf_state.state == 'test_state'
        assert wf_state.label == 'TEST_LABEL'
        assert wf_state.status == WorkflowStatus.ACTIVE
        assert wf_state.params['param'] == 'value'
        assert wf_state.memory['mem'] == 'data'
        
        # Test immutability
        updated_state = wf_state.set(status=WorkflowStatus.COMPLETED)
        assert wf_state.status == WorkflowStatus.ACTIVE  # Original unchanged
        assert updated_state.status == WorkflowStatus.COMPLETED  # New instance updated
        
        # Test WorkflowStep creation
        step = WorkflowStep(
            workflow_id=wf_state._id,
            title='Test Step',
            label='CREATED',
            stage='test_stage',
            status=StepStatus.ACTIVE
        )
        
        assert step.workflow_id == wf_state._id
        assert step.title == 'Test Step'
        assert step.label == 'CREATED'
        assert step.stage == 'test_stage'
        assert step.status == StepStatus.ACTIVE

    def test_label_validation(self):
        """Test label validation functionality"""
        # Valid labels (uppercase)
        result = validate_labels('CREATED', 'PROCESSING', 'COMPLETED')
        assert result == ('CREATED', 'PROCESSING', 'COMPLETED')
        
        # Invalid labels should raise ValueError
        with pytest.raises(ValueError, match='Invalid step state'):
            validate_labels('invalid_label')  # lowercase
            
        with pytest.raises(ValueError, match='Invalid step state'):
            validate_labels('CREATED', 'invalid')  # mixed case

    def test_workflow_and_step_status_categories(self):
        """Test status categorization"""
        # Workflow status categories
        assert WorkflowStatus.ACTIVE in WorkflowStatus._ACTIVE
        assert WorkflowStatus.ERROR in WorkflowStatus._ACTIVE
        assert WorkflowStatus.PAUSED in WorkflowStatus._ACTIVE
        
        assert WorkflowStatus.BLANK in WorkflowStatus._INACTIVE
        assert WorkflowStatus.CANCELLED in WorkflowStatus._INACTIVE
        assert WorkflowStatus.COMPLETED in WorkflowStatus._INACTIVE
        
        assert WorkflowStatus.COMPLETED in WorkflowStatus._FINISHED
        assert WorkflowStatus.FAILED in WorkflowStatus._FINISHED
        assert WorkflowStatus.CANCELLED in WorkflowStatus._FINISHED
        
        # Step status categories
        assert StepStatus.COMPLETED in StepStatus._FINISHED
        assert StepStatus.SKIPPED in StepStatus._FINISHED
        assert StepStatus.ABORTED in StepStatus._FINISHED
        assert StepStatus.ACTIVE not in StepStatus._FINISHED

    def test_workflow_configuration_validation(self):
        """Test workflow configuration validation"""
        stage = Stage('Validation Stage')
        
        # Test transition to non-existent state (this should fail first)
        with pytest.raises(WorkflowConfigurationError, match='State .* is not define in Step states'):
            class InvalidStateStep(Step, title='Invalid State Step', stage=stage):
                # Using default states: ('CREATED', 'RUNNING', 'FINISHED')
                @transition('NONEXISTENT')  # Not in default states!
                def invalid_transition(self):
                    pass

        # Test duplicate transition handlers (need to use valid states)
        with pytest.raises(WorkflowConfigurationError, match='Duplicated transition handler'):
            class DuplicateTransitionStep(Step, title='Duplicate Step', stage=stage):
                # Using default states: ('CREATED', 'RUNNING', 'FINISHED')
                @transition('RUNNING')
                def first_transition(self):
                    pass
                    
                @transition('RUNNING')  # Duplicate!
                def second_transition(self):
                    pass

    def test_workflow_manager_functionality(self):
        """Test WorkflowManager operations"""
        class ManagerWorkflow(Workflow, title='Manager Workflow', revision=1):
            stage = Stage('Manager Stage')
            
            @wf_connect('manager-event')
            def handle_manager_event(wf_state, event):
                yield f"Handled: {event.data}"
                
            class ManagerStep(Step, title='Manager Step', stage=stage):
                pass
                
        # Test manager initialization
        manager = WorkflowManager()
        assert hasattr(manager, '_running')
        
        # Verify workflow is registered (with kebab-case key)
        assert 'manager-workflow' in WorkflowManager.__registry__
        
        # Test that process_event method exists
        assert hasattr(manager, 'process_event')
        assert callable(manager.process_event)

    def test_role_and_stage_components(self):
        """Test role and stage definitions"""
        # Test Stage
        stage1 = Stage('First Stage', order=1)
        stage2 = Stage('Second Stage', order=2)
        
        assert stage1.__title__ == 'First Stage'
        assert stage1.__order__ == 1
        assert stage2.__title__ == 'Second Stage'
        assert stage2.__order__ == 2
        
        # Test Role
        admin = Role('Administrator')
        user = Role('User')
        
        assert admin.__title__ == 'Administrator'
        assert user.__title__ == 'User'

    def test_step_multi_instance_configuration(self):
        """Test step multi-instance settings"""
        stage = Stage('Multi Stage')
        
        # Default single instance
        class SingleStep(Step, title='Single Step', stage=stage):
            pass
            
        assert SingleStep.__multi__ == False
        
        # Multi-instance enabled
        class MultiStep(Step, title='Multi Step', stage=stage, multi=True):
            pass
            
        assert MultiStep.__multi__ == True

    def test_transition_all_states_support(self):
        """Test transitions allowed from all states"""
        stage = Stage('Emergency Stage')
        
        class EmergencyStep(Step, title='Emergency Step', stage=stage):
            __states__ = ('CREATED', 'PROCESSING', 'COMPLETED', 'EMERGENCY')
            
            @transition('EMERGENCY', allowed_states=(ALL_STATES,))
            def emergency_stop(self):
                return {'message': 'Emergency stop'}
                
        # Verify ALL_STATES transition
        allowed_states, _ = EmergencyStep.__transitions__['EMERGENCY']
        assert allowed_states == (ALL_STATES,)

    def test_step_lifecycle_hooks(self):
        """Test step lifecycle hook methods"""
        stage = Stage('Lifecycle Stage')
        
        class LifecycleStep(Step, title='Lifecycle Step', stage=stage):
            def on_created(self, step):
                pass
                
            def on_finish(self, step):
                pass
                
            def on_finished(self, step):
                pass
                
            def on_error(self, step):
                pass
                
            def on_recovery(self, step):
                pass
                
        # Verify lifecycle methods exist
        step_instance = LifecycleStep()
        assert hasattr(step_instance, 'on_created')
        assert hasattr(step_instance, 'on_finish')
        assert hasattr(step_instance, 'on_finished')
        assert hasattr(step_instance, 'on_error')
        assert hasattr(step_instance, 'on_recovery')

    def test_workflow_lifecycle_hooks(self):
        """Test workflow lifecycle hooks"""
        class LifecycleWorkflow(Workflow, title='Lifecycle Workflow', revision=1):
            stage = Stage('Lifecycle Stage')
            
            def on_started(wf_state, wf_params):
                yield "Workflow started"
                
            def on_finish(wf_state):
                yield "Workflow finished"
                
            def on_terminate(wf_state):
                yield "Workflow terminated"
                
            def on_reconcile(wf_state):
                yield "Workflow reconciled"
                
            class LifecycleStep(Step, title='Lifecycle Step', stage=stage):
                pass
                
        # Verify lifecycle hooks exist
        assert hasattr(LifecycleWorkflow, 'on_started')
        assert hasattr(LifecycleWorkflow, 'on_finish')
        assert hasattr(LifecycleWorkflow, 'on_terminate')
        assert hasattr(LifecycleWorkflow, 'on_reconcile')

    def test_error_conditions(self):
        """Test error handling and edge cases"""
        stage = Stage('Error Stage')
        
        # Test invalid start state
        with pytest.raises(ValueError, match='Invalid start states'):
            class InvalidStartStep(Step, title='Invalid Start Step', stage=stage):
                __states__ = ('CREATED', 'PROCESSING', 'COMPLETED')
                __start__ = 'INVALID_START'  # Not in __states__

    def test_comprehensive_workflow_integration(self):
        """Test a complete workflow with all components"""
        class CompleteWorkflow(Workflow, title='Complete Workflow', revision=1):
            """A comprehensive workflow demonstrating all features"""
            
            # Stages with ordering
            init_stage = Stage('Initialization', order=1)
            proc_stage = Stage('Processing', order=2)
            final_stage = Stage('Finalization', order=3)
            
            # Roles
            admin_role = Role('Administrator')
            user_role = Role('User')
            
            # Workflow-level event handlers
            @wf_connect('workflow-start')
            def handle_start(wf_state, event):
                yield f"Workflow started: {event.data}"
                
            @wf_connect('workflow-complete')
            def handle_complete(wf_state, event):
                yield f"Workflow completed: {event.data}"
                
            # Steps with state machines and event handlers
            class InitStep(Step, title='Initialization Step', stage=init_stage):
                __states__ = ('CREATED', 'INITIALIZING', 'INITIALIZED', 'FAILED')
                __start__ = 'CREATED'
                
                @st_connect('init-start')
                def handle_init_start(step_state, event):
                    yield f"Init started: {event.data}"
                    
                @transition('INITIALIZING')
                def start_init(self):
                    return {'message': 'Initialization started'}
                    
                @transition('INITIALIZED', allowed_states=('INITIALIZING',))
                def complete_init(self):
                    return {'message': 'Initialization completed'}
                    
                @transition('FAILED')
                def fail_init(self):
                    return {'message': 'Initialization failed'}
                    
            class ProcessStep(Step, title='Processing Step', stage=proc_stage, multi=True):
                __states__ = ('CREATED', 'PROCESSING', 'COMPLETED', 'ERROR')
                
                @st_connect('process-data')
                def handle_process_data(step_state, event):
                    yield f"Processing data: {event.data}"
                    
                @transition('PROCESSING')
                def start_processing(self):
                    return {'message': 'Processing started'}
                    
                @transition('COMPLETED', allowed_states=('PROCESSING',))
                def complete_processing(self):
                    return {'message': 'Processing completed'}
                    
                @transition('ERROR')
                def error_processing(self):
                    return {'message': 'Processing error'}
                    
            class FinalStep(Step, title='Final Step', stage=final_stage):
                @st_connect('finalize')
                def handle_finalize(step_state, event):
                    yield f"Finalizing: {event.data}"
                    
        # Verify workflow registration (kebab-case key)
        assert 'complete-workflow' in WorkflowManager.__registry__
        assert CompleteWorkflow.__title__ == 'Complete Workflow'
        
        # Verify stages
        assert CompleteWorkflow.init_stage.__title__ == 'Initialization'
        assert CompleteWorkflow.init_stage.__order__ == 1
        assert CompleteWorkflow.proc_stage.__title__ == 'Processing'
        assert CompleteWorkflow.proc_stage.__order__ == 2
        assert CompleteWorkflow.final_stage.__title__ == 'Finalization'
        assert CompleteWorkflow.final_stage.__order__ == 3
        
        # Verify roles
        assert CompleteWorkflow.admin_role.__title__ == 'Administrator'
        assert CompleteWorkflow.user_role.__title__ == 'User'
        
        # Verify steps
        assert CompleteWorkflow.InitStep.__states__ == ('CREATED', 'INITIALIZING', 'INITIALIZED', 'FAILED')
        assert CompleteWorkflow.InitStep.__start__ == 'CREATED'
        assert CompleteWorkflow.ProcessStep.__multi__ == True
        assert CompleteWorkflow.ProcessStep.__states__ == ('CREATED', 'PROCESSING', 'COMPLETED', 'ERROR')
        
        # Verify event handlers are registered
        expected_events = ['workflow-start', 'workflow-complete', 'init-start', 'process-data', 'finalize']
        for event in expected_events:
            assert event in EventRouter.ROUTING_TABLE
            
        # Verify transitions
        assert len(CompleteWorkflow.InitStep.__transitions__) == 3
        assert len(CompleteWorkflow.ProcessStep.__transitions__) == 3
        
        # Verify manager can handle this workflow
        manager = WorkflowManager()
        assert 'complete-workflow' in manager.__registry__

    def test_stm_state_transitions_and_memory(self):
        """Test workflow state management and memory operations"""
        # Create workflow state
        wf_state = WorkflowState(
            state='memory_test',
            label='MEMORY_TEST',
            status=WorkflowStatus.BLANK,
            params={'initial_param': 'value'},
            memory={}
        )
        
        # Test status transitions
        active_state = wf_state.set(status=WorkflowStatus.ACTIVE)
        assert active_state.status == WorkflowStatus.ACTIVE
        assert wf_state.status == WorkflowStatus.BLANK  # Original unchanged
        
        # Test memory operations
        memory_state = active_state.set(
            memory={'step_count': 0, 'last_action': 'started'}
        )
        assert memory_state.memory['step_count'] == 0
        assert memory_state.memory['last_action'] == 'started'
        
        # Test parameter updates
        param_state = memory_state.set(
            params={**memory_state.params, 'new_param': 'new_value'}
        )
        assert param_state.params['initial_param'] == 'value'
        assert param_state.params['new_param'] == 'new_value'

    def test_step_data_management(self):
        """Test step data management and relationships"""
        workflow_id = UUID_GENF('test-workflow')
        parent_id = UUID_GENF('parent-step')
        child_id = UUID_GENF('child-step')
        
        # Create parent step
        parent_step = WorkflowStep(
            _id=parent_id,
            workflow_id=workflow_id,
            title='Parent Step',
            label='CREATED',
            stage='parent_stage',
            status=StepStatus.ACTIVE,
            src_step_id=None  # Root step
        )
        
        # Create child step
        child_step = WorkflowStep(
            _id=child_id,
            workflow_id=workflow_id,
            title='Child Step',
            label='CREATED',
            stage='child_stage',
            status=StepStatus.ACTIVE,
            src_step_id=parent_id  # Child of parent
        )
        
        # Verify relationships
        assert parent_step.src_step_id is None
        assert child_step.src_step_id == parent_id
        assert parent_step.workflow_id == child_step.workflow_id
        
        # Test step updates
        updated_parent = parent_step.set(
            label='PROCESSING',
            status=StepStatus.ACTIVE
        )
        
        assert updated_parent.label == 'PROCESSING'
        assert parent_step.label == 'CREATED'  # Original unchanged 
