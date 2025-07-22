from fluvius.helper import timestamp
from . import logger, config
from .datadef import WorkflowData, WorkflowStatus, WorkflowMessage, WorkflowEvent
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
            wf = wf_engine.create_workflow(route_id, {"started": timestamp()})
            self._running[workflow_key, route_id] = wf

        return self._running[workflow_key, route_id]
    
    async def _log_mutation(self, tx, wf_mut: MutationEnvelop):
        await tx.insert_many('workflow-mutation', wf_mut.model_dump())

    async def _log_event(self, tx, wf_evt: WorkflowEvent):
        """Add a workflow event record."""
        logger.warning(f"Logging event: {wf_evt.model_dump()}")
        await tx.insert_many('workflow-event', wf_evt.model_dump())
    
    async def _log_message(self, tx, wf_msg: WorkflowMessage):
        """Add a workflow message record."""
        await tx.insert_many('workflow-message', wf_msg.model_dump())
    
    async def persist_events(self, tx, events: list[WorkflowEvent]):
        events = tuple(events)
        """
        Persist a list of WorkflowEvent objects to the database.
        
        Args:
            events: List of WorkflowEvent objects to persist
        """
        for evt in events:
            await self._log_event(tx, evt)

        return events
    
    async def persist_messages(self, tx, messages: list[WorkflowMessage]):
        """
        Persist a list of WorkflowMessage objects to the database.
        
        Args:
            messages: List of WorkflowMessage objects to persist
        """
        messages = tuple(messages)
        for msg in messages:
            await self._log_message(tx, msg)
        
        return messages
    
    async def persist_mutations(self, tx, mutations: list[MutationEnvelop]):
        """
        Persist a list of MutationEnvelop objects to the database.
        
        Args:
            mutations: List of MutationEnvelop objects to persist
        """
        mutations = tuple(mutations)
        for wf_mut in mutations:
            try:
                await self._log_mutation(tx, wf_mut)
                await self._persist_single_mutation(tx, wf_mut)                    
            except Exception as e:
                logger.error(f"Failed to persist mutation {wf_mut.action}: {e}")
                raise        
        return mutations
    
    async def persist(self, wf: WorkflowEngine):
        """
        Persist a list of MutationEnvelop objects to the database.
        
        Args:
            mutations: List of MutationEnvelop objects to persist
            
        Returns:
            dict: Summary of persisted mutations by type
        """
        mutations, messages, events = wf.commit()

        async with self._datamgr.transaction() as tx:
            mutations = await self.persist_mutations(self._datamgr, mutations)
            messages = await self.persist_messages(self._datamgr, messages)
            events = await self.persist_events(self._datamgr, events)

        logger.info(f"Persisted {len(mutations)} mutations, {len(messages)} messages, {len(events)} events")
        return mutations, messages, events

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

    async def _persist_single_mutation(self, tx, wf_mut: MutationEnvelop):
        """Persist a single mutation to the database."""
        mutation_key = wf_mut.mutation.__key__
        handlers = self._get_mutation_handlers()
        
        if mutation_key in handlers:
            await handlers[mutation_key](tx, wf_mut)
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

    async def _persist_create_workflow(self, tx, wf_mut: MutationEnvelop):
        """Create a new workflow record."""
        wf_data = wf_mut.mutation.workflow
        workflow_dict = self._map_object_to_dict(wf_data, self.WORKFLOW_FIELD_MAP)
        await tx.insert_many('workflow', workflow_dict)

    async def _persist_update_workflow(self, tx, wf_mut: MutationEnvelop):
        """Update an existing workflow record."""
        mutation = wf_mut.mutation
        updates = self._extract_updates(mutation, self.WORKFLOW_UPDATE_FIELDS)
            
        if updates:
            await tx.update_one('workflow', wf_mut.workflow_id, **updates)

    async def _persist_add_step(self, tx, wf_mut: MutationEnvelop):
        """Add a new step record."""
        step_data = wf_mut.mutation.step.model_dump()
        await tx.insert_many('workflow-step', step_data)

    async def _persist_update_step(self, tx, wf_mut: MutationEnvelop):
        """Update an existing step record."""
        mutation = wf_mut.mutation
        updates = self._extract_updates(mutation, self.STEP_UPDATE_FIELDS)
            
        if updates and wf_mut.step_id:
            await tx.update_one('workflow-step', wf_mut.step_id, **updates)

    async def _persist_set_memory(self, tx, wf_mut: MutationEnvelop):
        """Set workflow or step memory records."""
        values = wf_mut.mutation.model_dump()
        
        # Process each key-value pair in the memory data
        for key, value in values.items():
            if value is None:
                del values[key]

        values['workflow_id'] = wf_mut.workflow_id

        await tx.upsert_many('workflow-memory', values)

    async def _persist_add_trigger(self, tx, wf_mut: MutationEnvelop):
        """Add a trigger record."""
        trigger = wf_mut.mutation
        
        # Field mapping for trigger data
        trigger_fields = {
            'workflow_id': wf_mut.workflow_id,
            'origin_step': wf_mut.step_id,
            'trigger_name': trigger.name,
            'trigger_data': trigger.data
        }
        
        await tx.insert_many('workflow-trigger', trigger_fields)

    async def _persist_add_participant(self, tx, wf_mut: MutationEnvelop):
        """Add a participant record."""
        participant = wf_mut.mutation
        
        # Field mapping for participant data
        participant_fields = {
            'workflow_id': wf_mut.workflow_id,
            'user_id': participant.user_id,
            'role': participant.role
        }
        
        await tx.insert_many('workflow-participant', participant_fields)

    async def _persist_del_participant(self, tx, wf_mut: MutationEnvelop):
        """Remove a participant record."""
        participant = wf_mut.mutation
        
        # Build query conditions
        query_conditions = {
            'workflow_id': wf_mut.workflow_id
        }
        
        if participant.user_id:
            query_conditions['user_id'] = participant.user_id
            
        from fluvius.data.query import BackendQuery
        query = BackendQuery.create(**query_conditions)

        # Find the record first, then remove it
        record = await tx.find_one('workflow-participant', **query_conditions)
        if record:
            await tx.remove(record)

    async def _persist_add_stage(self, tx, wf_mut: MutationEnvelop):
        """Add a stage record."""
        stage_data = wf_mut.mutation.data.model_dump()
        stage_data['workflow_id'] = wf_mut.workflow_id

        await tx.insert_many('workflow-stage', stage_data)

    @classmethod
    def register(cls, wf_cls):
        workflow_key = wf_cls.Meta.key
        if workflow_key in cls.__registry__:
            raise ValueError(f'Worfklow already registered: {workflow_key}')

        cls.__registry__[workflow_key] = type(f'WFE_{wf_cls.__name__}', (cls.__engine__, ), {}, wf_def=wf_cls)
        logger.info('Registered workflow: %s', workflow_key)

