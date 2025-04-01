# from functools import partial
# from .cfg import logger, config  # noqa

# from fluvius.data import UUID_GENR, C, UUID_GENF, PropertyList, Q
# from fluvius.base.helper import camel_to_lower

# from .resource import WorkflowDAL, WorkflowInstance, WorkflowMemory, WorkflowParams
# from .status import WorkflowStatus
# from .workflow import WorkflowRegistry


# class WorkflowStepStateManager(object):
#     def __init__(self, engine, step):
#         self.update_step = partial(engine.update_step, step_id=step._id)
#         self.set_status = partial(engine.set_status, step_id=step._id)
#         self.memorize = partial(engine.memorize, step_id=step._id)
#         self.add_participant = engine.add_participant
#         self.remove_participant = engine.remove_participant
#         self.user_action = engine.user_action
#         self.send_action = engine.send_action
#         self.get_step = engine.get_step
#         self.create_step = partial(engine.create_step, src_step=step._id)

#         def _wrap(values):
#             for k, value in values.items():
#                 _, _, key = k.partition(':')
#                 yield key, value

#         def memorize(**kwargs):
#             return engine.memorize(**{
#                 f'{step._id}:{key}': value for key, value in kwargs.items()
#             })

#         def step_memory(*args):
#             results = engine.get_memory(**[f'{step._id}:{key}' for key in args])
#             return dict(_wrap(results))

#         def worfklow_memory(*args):
#             return engine.get_memory(**args)

#         self.step_memory = step_memory
#         self.worfklow_memory = worfklow_memory


# class WorkflowStateManager(object):
#     def __init__(self, engine):
#         self.memorize = partial(engine.memorize, step_id=None)
#         self.update_step = engine.update_step
#         self.set_status = engine.set_status
#         self.add_participant = engine.add_participant
#         self.remove_participant = engine.remove_participant
#         self.user_action = engine.user_action
#         self.send_action = engine.send_action
#         self.get_step = engine.get_step
#         self.create_step = engine.create_step

#         def _wrap(values):
#             for k, value in values.items():
#                 _, _, key = k.partition(':')
#                 yield key, value

#         def worfklow_memory(*args):
#             return engine.get_memory(**args)

#         self.worfklow_memory = worfklow_memory


# class WorkflowStep(object):
#     def __init__(self, step):
#         self._id = step._id
#         self.data = step

#     def __init_subclass__(cls, name=None, stage=None):
#         cls._identifier = camel_to_lower(name or cls.__name__)
#         cls._stage = stage

#     @classmethod
#     def defaults(cls, **params):
#         return C(
#             title=cls.__name__,
#             step_name=cls._identifier
#         )


# class WorkflowStage(object):
#     def __init_subclass__(cls, name=None):
#         cls._identifier = camel_to_lower(name or cls.__name__)

#     def __init__(self, name=None):
#         if name is not None:
#             self._identifier = name


# class WorkflowEngine(object):
#     _db = WorkflowDAL

#     def __init__(self, workflow, context):
#         self._context = context
#         self._workflow = WorkflowRegistry.construct(workflow.identifier, workflow)
#         self._steps = {}
#         self._memory = PropertyList(workflow._id, WorkflowMemory)
#         self._params = PropertyList(workflow._id, WorkflowParams)

#     @classmethod
#     def create(cls, context, wf_name, _id=None, **params):
#         wf_cls = WorkflowRegistry.get(wf_name)
#         workflow = WorkflowInstance.create(
#             _id=_id or UUID_GENR(),
#             identifier=wf_name,
#             title=wf_cls.__title__,
#             revison=wf_cls.__revision__,
#             desc=wf_cls.__doc__,
#             status=WorkflowStatus.BLANK,
#             owner_id=context.user_id
#         )
#         return cls(workflow, context)

#     @classmethod
#     async def load(cls, context, wf_name, _id):
#         workflow = await cls._db.fetch('workflow-instance', _id, identifier=wf_name)
#         return cls(workflow, context)

#     async def commit(self):
#         return await self.save_state()

#     @property
#     def state(self):
#         return self._state

#     @property
#     def steps(self):
#         return self._steps

#     @property
#     def workflow(self):
#         return self._workflow

#     @property
#     def db(self):
#         return self._db

#     @property
#     def memory(self):
#         return self._memory

#     @property
#     def params(self):
#         return self._params

#     async def fetch_memory(self):
#         values = await self.db.find('workflow-memory', Q(where={"workflow_id": self.workflow._id}))
#         self._memory.load(values)

#     async def fetch_params(self):
#         values = self.db.find('workflow-params', Q(where={"workflow_id": self.workflow._id}))
#         self._params.load(values)

#     def input_step_event(self, event_name, step_id, event_data=None):
#         return self.process_event(event_name, f'on_{event_name}', step_id, None, event_data)

#     def input_workflow_event(self, event_name, event_data):
#         return self.process_event(event_name, f'on_{event_name}', None, None, event_data)

#     async def trigger(self, event_name, handler_name, step_id, step_name, event_data):
#         if step_id is not None:
#             step = await self.get_step(step_id, step_name)
#             evt_handler = getattr(step, handler_name)
#             statemgr = WorkflowStepStateManager(self, step)
#         else:
#             evt_handler = getattr(self.workflow, handler_name)
#             statemgr = WorkflowStateManager(self)

#         return list(evt_handler(statemgr, event_name, event_data))

#     def process_event(self, event_name, handler_name, step_id, event_data):
#         return list(self.trigger(event_name, handler_name, step_id, event_data))

#     async def save_state(self):
#         await self.db.upsert('workflow-instance', self.workflow.data.serialize())
#         for stage in self.workflow._stages.values():
#             await self.db.upsert('workflow-stage', stage.data(self.workflow._id).serialize())

#         for step in self.steps.values():
#             await self.db.upsert('workflow-step', step.data.serialize())

#         for k, v in self._memory.changes():
#             await self.db.upsert('workflow-memory', v.serialize())

#     def _fetch_step(self, step_id, step_name):
#         if step_name:
#             return self.db.fetch('workflow-step', step_id, workflow_id=self.workflow._id, step_name=step_name)

#         return self.db.fetch('workflow-step', step_id, workflow_id=self.workflow._id)

#     def memorize(self, step_id=None, **kwargs):
#         self.memory.set(_scope=step_id, **kwargs)

#     def update_step(self, step_id, _id=None, **kwargs):
#         step = self.steps[step_id]
#         self.steps[step_id] = step.set(**kwargs)
#         return self.steps[step_id]

#     def set_status(self, step_id, step_status=None, display_status=None):
#         return self.update_step(
#             step_id,
#             step_status=step_status,
#             display_status=display_status
#         )

#     def create_step(self, step_name, src_step=None, **kwargs):
#         step_cls = self.workflow._step_cls[step_name]
#         stage_id = UUID_GENF(step_cls._stage, self.workflow._id)
#         data = dict(
#             step_name=step_name,
#             workflow_id=self.workflow._id,
#             stage_id=stage_id,
#             status="ACTIVE",
#             title=step_cls.__name__,
#             src_step=src_step,
#         )
#         step = self.db.create('workflow-step', data)
#         self.steps[step._id] = step_cls(step)
#         self.memorize(**kwargs, step_id=step._id)
#         return self.steps[step._id]

#     async def get_step(self, step_id, step_name=None):
#         if step_id is None:
#             return None

#         if step_id not in self._steps:
#             step_data = await self._fetch_step(step_id, step_name)
#             step_cls = self.workflow._step_cls[step_data.step_name]
#             self._steps[step_id] = step_cls(step_data)

#         return self._steps[step_id]

#     def add_participant(self, step_key, _id=None, **kwargs):
#         self.steps[step_key] = kwargs

#     def remove_participant(self, step_key, _id=None, **kwargs):
#         self.steps[step_key] = kwargs

#     def user_action(self, **kwargs):
#         pass

#     def send_action(self, **kwargs):
#         pass
