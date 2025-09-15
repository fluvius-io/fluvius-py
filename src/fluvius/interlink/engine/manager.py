from fluvius.helper import timestamp
from .. import logger, config
from ..model import WorkflowDataManager

from .datadef import WorkflowData, WorkflowStatus, WorkflowMessage, WorkflowActivity
from .router import ActivityRouter
from .runner import WorkflowRunner
from .mutation import (
    MutationEnvelop,
    get_mutation
)
from fluvius.data import UUID_GENF

class WorkflowManager(object):
    __router__ = ActivityRouter
    __runner__ = WorkflowRunner
    __registry__ = {}

    def __init__(self, datamgr=None):
        self._wfbyres= {}
        self._wfbyids = {}
        self._datamgr = datamgr or WorkflowDataManager(self)

        assert isinstance(self._datamgr, WorkflowDataManager), "Workflow manager requires WorkflowDataManager"

    def __init_subclass__(cls, router, engine):
        assert issubclass(router, ActivityRouter), f"Invalid event router {router}"
        assert issubclass(engine, WorkflowRunner), f"Invalid workflow engine {engine}"

        cls.__router__ = router
        cls.__runner__ = engine
        cls.__registry__ = {}

    async def process_event(self, event_name, event_data):
        for trigger in self.route_event(event_name, event_data):
            wf = await self.load_workflow(
                trigger.wfdef_key,
                trigger.resource_name,
                trigger.resource_id
            )

            with wf.transaction():
                wf.trigger(trigger)

            yield wf

    def route_event(self, event_name, event_data):
        return self.__router__.route_event(event_name, event_data)
    
    def create_workflow(self, wfdef_key, resource_name, resource_id, params=None, title=None):
        wf_engine = self.__registry__[wfdef_key]
        wf = wf_engine.create_workflow(resource_name, resource_id, params or {}, title=title)
        self._wfbyres[wfdef_key, resource_name, resource_id] = wf
        self._wfbyids[wfdef_key, wf.id] = wf
        return wf

    async def load_workflow(self, wfdef_key, resource_name, resource_id):
        if not resource_id:
            raise ValueError('Invalid workflow resource: {resource}:{resource_id}')

        if (wfdef_key, resource_name, resource_id) not in self._wfbyres:
            wf_engine = self.__registry__[wfdef_key]
            wf_data = await self._datamgr.find_one('_workflow', where=dict(
                wfdef_key=wfdef_key,
                resource_name=resource_name,
                resource_id=resource_id
            ))
            wf = wf_engine(wf_data)
            self._wfbyres[wfdef_key, resource_name, resource_id] = wf
            self._wfbyids[wfdef_key, wf.id] = wf

        return self._wfbyres[wfdef_key, resource_name, resource_id]


    async def load_workflow_by_id(self, wfdef_key, workflow_id):
        if (wfdef_key, workflow_id) not in self._wfbyids:
            wf_engine = self.__registry__[wfdef_key]
            wf_data = await self._datamgr.fetch('_workflow', workflow_id, wfdef_key=wfdef_key)

            wf = wf_engine(wf_data)
            self._wfbyids[wfdef_key, workflow_id] = wf
            self._wfbyres[wfdef_key, wf.resource_name, wf.resource_id] = wf

        return self._wfbyids[wfdef_key, workflow_id]
    
    async def _log_mutation(self, tx, wf_mut: MutationEnvelop):
        await tx.insert_many('workflow-mutation', wf_mut.model_dump())

    async def _log_activity(self, tx, wf_act: WorkflowActivity):
        """Add a workflow event record."""
        await tx.insert_many('workflow-activity', wf_act.model_dump())
    
    async def _log_message(self, tx, wf_msg: WorkflowMessage):
        """Add a workflow message record."""
        await tx.insert_many('workflow-message', wf_msg.model_dump())
    
    async def persist_activities(self, tx, activities: list[WorkflowActivity]):
        activities = tuple(activities)
        """
        Persist a list of WorkflowActivity objects to the database.
        
        Args:
            activities: List of WorkflowActivity objects to persist
        """
        for act in activities:
            await self._log_activity(tx, act)

        return activities
    
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
                await self._persist_single_mutation(tx, wf_mut)                    
                await self._log_mutation(tx, wf_mut)
            except Exception as e:
                logger.error(f"Failed to persist mutation {wf_mut.action}: {e}")
                raise        
        return mutations
    
    async def persist(self, tx, wf: WorkflowRunner):
        """
        Persist a list of MutationEnvelop objects to the database.
        
        Args:
            mutations: List of MutationEnvelop objects to persist
            
        Returns:
            dict: Summary of persisted mutations by type
        """
        mutations, messages, activities = wf.commit()

        mutations = await self.persist_mutations(tx, mutations)
        messages = await self.persist_messages(tx, messages)
        activities = await self.persist_activities(tx, activities)

        logger.info(f"Persisted {len(mutations)} mutations, {len(messages)} messages, {len(activities)} events")
        return mutations, messages, activities

    def _get_mutation_handlers(self):
        """Build dispatch table using mutation registry keys."""
        return {
            'initialize-workflow': self._persist_initialize_workflow,
            'update-workflow': self._persist_update_workflow,
            'add-step': self._persist_add_step,
            'update-step': self._persist_update_step,
            'set-memory': self._persist_set_memory,
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
                # Convert UUID objects to strings for resource_id
                if source_field == 'resource_id' and value is not None:
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

    async def _persist_initialize_workflow(self, tx, wf_mut: MutationEnvelop):
        """Create a new workflow record."""
        wf_data = wf_mut.mutation.workflow
        workflow_dict = wf_data.model_dump()
        await tx.insert_many('workflow', workflow_dict)

    async def _persist_update_workflow(self, tx, wf_mut: MutationEnvelop):
        """Update an existing workflow record."""
        updates = wf_mut.mutation.model_dump(exclude_none=True)
            
        if updates:
            await tx.update_one('workflow', wf_mut.workflow_id, **updates)

    async def _persist_add_step(self, tx, wf_mut: MutationEnvelop):
        """Add a new step record."""
        step_data = wf_mut.mutation.step.model_dump()
        await tx.insert_many('workflow-step', step_data)

    async def _persist_update_step(self, tx, wf_mut: MutationEnvelop):
        """Update an existing step record."""
        updates = wf_mut.mutation.model_dump(exclude_none=True)            
        if updates:
            await tx.update_one('workflow-step', wf_mut.step_id, **updates)

    async def _persist_set_memory(self, tx, wf_mut: MutationEnvelop):
        """Set workflow or step memory records."""
        values = wf_mut.mutation.model_dump(exclude_none=True)
        values['_id'] = wf_mut.workflow_id
        values['workflow_id'] = wf_mut.workflow_id
        await tx.upsert_many('workflow-memory', values)

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
        wfdef_key = wf_cls.Meta.key
        if wfdef_key in cls.__registry__:
            raise ValueError(f'Worfklow already registered: {wfdef_key}')

        cls.__registry__[wfdef_key] = type(f'WFE_{wf_cls.__name__}', (cls.__runner__, ), {}, wf_def=wf_cls)
        logger.warning('Registered workflow: %s', wfdef_key)
    

    async def commit(self):
        for wf in self._wfbyres.values():
            await self.persist(self._datamgr, wf)
    

    async def commit_workflow(self, wf: WorkflowRunner):
        await self.persist(self._datamgr, wf)
        return wf

