from . import logger, config
from .datadef import WorkflowData, WorkflowStatus
from .router import ActivityRouter
from .engine import WorkflowEngine
from .domain.model import WorkflowDataManager
from .mutation import (
    MutationEnvelop, CreateWorkflow, UpdateWorkflow, AddStep, UpdateStep, 
    SetMemory, AddTrigger, AddParticipant, DelParticipant, AddStage, REGISTRY
)
from fluvius.data import UUID_GENR

class WorkflowManager(object):
    __router__ = ActivityRouter
    __engine__ = WorkflowEngine
    __datamgr__ = WorkflowDataManager
    __registry__ = {}

    # Field mappings for database operations
    WORKFLOW_FIELD_MAP = {
        'id': '_id',
        'title': 'title',
        'revision': 'revison',  # Note: matches schema typo
        'route_id': 'route_id',
        'status': 'status',
        'progress': 'progress',
        'ts_start': 'ts_start',
        'ts_expire': 'ts_expire',
        'ts_finish': 'ts_finish',
        'ts_transit': 'ts_transit'
    }

    WORKFLOW_UPDATE_FIELDS = [
        'status', 'progress', 'etag', 'ts_start', 
        'ts_expire', 'ts_finish', 'ts_transit'
    ]

    STEP_FIELD_MAP = {
        'id': '_id',
        'workflow_id': 'workflow_id',
        'origin_step': 'origin_step',
        'stm_state': 'stm_state',
        'selector': 'step_name',  # Using selector as step_name
        'title': 'title',
        'status': 'status',
        'label': 'label',
        'ts_due': 'ts_due',
        'ts_start': 'ts_start',
        'ts_finish': 'ts_finish'
    }

    STEP_UPDATE_FIELDS = [
        'title', 'stm_state', 'message', 'status', 'label',
        'ts_due', 'ts_start', 'ts_finish', 'ts_transit'
    ]

    def __init__(self):
        self._running = {}
        self._datamgr = self.__datamgr__(self)

    def __init_subclass__(cls, router, engine):
        assert issubclass(router, ActivityRouter), f"Invalid event router {router}"
        assert issubclass(engine, WorkflowEngine), f"Invalid workflow engine {engine}"

        cls.__router__ = router
        cls.__engine__ = engine
        cls.__registry__ = {}

    def process_activity(self, activity_name, activity_data):
        for trigger in self.route_activity(activity_name, activity_data):
            wf = self.load_workflow(trigger.workflow_key, trigger.route_id)
            with wf.transaction() as wf_proxy:
                if wf.status == WorkflowStatus.NEW:
                    wf_proxy.start()
                wf_proxy.trigger(trigger)

            yield wf

    def route_activity(self, activity_name, activity_data):
        return self.__router__.route_activity(activity_name, activity_data)

    def load_workflow(self, workflow_key, route_id):
        if (workflow_key, route_id) not in self._running:
            wf_engine = self.__registry__[workflow_key]
            wf = wf_engine.create_workflow(route_id)
            self._running[workflow_key, route_id] = wf

        return self._running[workflow_key, route_id]

    async def persist_mutations(self, mutations: list[MutationEnvelop]):
        """
        Persist a list of MutationEnvelop objects to the database.
        
        Args:
            mutations: List of MutationEnvelop objects to persist
            
        Returns:
            dict: Summary of persisted mutations by type
        """
        # Initialize summary with all registered mutation keys
        summary = {key: 0 for key in REGISTRY.keys()}
        summary['total_processed'] = 0
        
        async with self._datamgr.transaction() as tx:
            for mutenv in mutations:
                try:
                    await self._persist_single_mutation(tx, mutenv)
                    summary['total_processed'] += 1
                    
                    # Update counter using mutation key directly
                    mutation_key = mutenv.mutation.__key__
                    if mutation_key in summary:
                        summary[mutation_key] += 1
                        
                except Exception as e:
                    logger.error(f"Failed to persist mutation {mutenv.action}: {e}")
                    raise

        logger.info(f"Persisted {summary['total_processed']} mutations: {summary}")
        return summary

    def _get_mutation_handlers(self):
        """Build dispatch table using mutation registry keys."""
        return {
            'create-workflow': self._persist_create_workflow,
            'update-workflow': self._persist_update_workflow,
            'add-step': self._persist_add_step,
            'update-step': self._persist_update_step,
            'set-memory': self._persist_set_memory,
            'add-trigger': self._persist_add_trigger,
            'add-participant': self._persist_add_participant,
            'del-participant': self._persist_del_participant,
            'add-stage': self._persist_add_stage
        }

    async def _persist_single_mutation(self, tx, mutenv: MutationEnvelop):
        """Persist a single mutation to the database."""
        mutation_key = mutenv.mutation.__key__
        handlers = self._get_mutation_handlers()
        
        if mutation_key in handlers:
            await handlers[mutation_key](tx, mutenv)
        else:
            logger.warning(f"Unknown mutation key: {mutation_key}")

    def _map_object_to_dict(self, obj, field_map):
        """Convert an object to a dictionary using field mapping."""
        result = {}
        for source_field, target_field in field_map.items():
            if hasattr(obj, source_field):
                value = getattr(obj, source_field)
                # Convert UUID objects to strings for route_id
                if source_field == 'route_id' and value is not None:
                    value = str(value)
                result[target_field] = value
        return result

    def _extract_updates(self, mutation, allowed_fields):
        """Extract non-None fields from mutation object."""
        updates = {}
        for field in allowed_fields:
            if hasattr(mutation, field):
                value = getattr(mutation, field)
                if value is not None:
                    updates[field] = value
        return updates

    async def _persist_create_workflow(self, tx, mutenv: MutationEnvelop):
        """Create a new workflow record."""
        wf_data = mutenv.mutation.workflow
        workflow_dict = self._map_object_to_dict(wf_data, self.WORKFLOW_FIELD_MAP)
        await tx.insert_data('workflow_schema', workflow_dict)

    async def _persist_update_workflow(self, tx, mutenv: MutationEnvelop):
        """Update an existing workflow record."""
        mutation = mutenv.mutation
        updates = self._extract_updates(mutation, self.WORKFLOW_UPDATE_FIELDS)
            
        if updates:
            await tx.update_data('workflow_schema', mutenv.workflow_id, **updates)

    async def _persist_add_step(self, tx, mutenv: MutationEnvelop):
        """Add a new step record."""
        step_data = mutenv.mutation.step
        step_dict = self._map_object_to_dict(step_data, self.STEP_FIELD_MAP)
        await tx.insert_data('workflow_step', step_dict)

    async def _persist_update_step(self, tx, mutenv: MutationEnvelop):
        """Update an existing step record."""
        mutation = mutenv.mutation
        updates = self._extract_updates(mutation, self.STEP_UPDATE_FIELDS)
            
        if updates and mutenv.step_id:
            await tx.update_data('workflow_step', mutenv.step_id, **updates)

    async def _persist_set_memory(self, tx, mutenv: MutationEnvelop):
        """Set workflow or step memory records."""
        memory_data = mutenv.mutation.data
        
        # Process each key-value pair in the memory data
        for key, value in memory_data.items():
            memory_dict = {
                'workflow_id': mutenv.workflow_id,
                'step_id': mutenv.step_id,
                'memory_key': key,
                'memory_value': value
            }
            # Use upsert to handle key updates
            await tx.upsert('workflow_memory', memory_dict)

    async def _persist_add_trigger(self, tx, mutenv: MutationEnvelop):
        """Add a trigger record."""
        trigger = mutenv.mutation
        
        # Field mapping for trigger data
        trigger_fields = {
            'workflow_id': mutenv.workflow_id,
            'origin_step': mutenv.step_id,
            'trigger_name': trigger.name,
            'trigger_data': trigger.data
        }
        
        await tx.insert_data('workflow_trigger', trigger_fields)

    async def _persist_add_participant(self, tx, mutenv: MutationEnvelop):
        """Add a participant record."""
        participant = mutenv.mutation
        
        # Field mapping for participant data
        participant_fields = {
            'workflow_id': mutenv.workflow_id,
            'user_id': participant.user_id,
            'role': participant.role
        }
        
        await tx.insert_data('workflow_participant', participant_fields)

    async def _persist_del_participant(self, tx, mutenv: MutationEnvelop):
        """Remove a participant record."""
        participant = mutenv.mutation
        
        # Build query conditions
        query_conditions = {
            'workflow_id': mutenv.workflow_id
        }
        
        if participant.user_id:
            query_conditions['user_id'] = participant.user_id
            
        from fluvius.data.query import BackendQuery
        query = BackendQuery.create(**query_conditions)
        await tx.remove_one('workflow_participant', query)

    async def _persist_add_stage(self, tx, mutenv: MutationEnvelop):
        """Add a stage record."""
        stage_data = mutenv.mutation.data
        
        # Dynamic field extraction for stage data
        stage_fields = {
            'workflow_id': mutenv.workflow_id
        }
        
        # Extract available fields from stage data
        stage_field_names = ['key', 'title', 'desc', 'order']
        for field_name in stage_field_names:
            if hasattr(stage_data, field_name):
                stage_fields[field_name] = getattr(stage_data, field_name)
                 
        await tx.insert_data('workflow_stage', stage_fields)

    @classmethod
    def register(cls, wf_cls):
        workflow_key = wf_cls.Meta.key
        if workflow_key in cls.__registry__:
            raise ValueError(f'Worfklow already registered: {workflow_key}')

        cls.__registry__[workflow_key] = type(f'WFE_{wf_cls.__name__}', (cls.__engine__, ), {}, wf_def=wf_cls)
        logger.info('Registered workflow: %s', workflow_key)

