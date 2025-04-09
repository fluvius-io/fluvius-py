# from .cfg import logger, config  # noqa

# from fluvius.data.data_contract import DataContract, field
# from fluvius.data import UUID_GENF, nullable
# from fluvius.helper.registry import ClassRegistry
# from fluvius.helper import camel_to_lower

# from .resource import WorkflowInstance, WorkflowStage as WorkflowStageResource
# from .router import EventRouter


# class Workflow(DataContract):
#     name = field(str, mandatory=True)
#     desc = field(str, mandatory=True)
#     steps = field(list, initial=[])
#     stages = field(list, initial=[])
#     parameters = field(dict, initial={})
#     participants = field(list, initial=[])
#     status = field()


# class WorkflowEvent(DataContract):
#     workflow_id = field(mandatory=True)
#     workflow_name = field(mandatory=True)
#     event_name = field(str)
#     event_data = field()
#     step_id = field(nullable(str), initial=None)
#     step_name = field(nullable(str))


# class Step(object):
#     def __init__(self, step):
#         self._id = step._id
#         self.data = step

#     def __init_subclass__(cls, name=None, stage=None):
#         cls._identifier = name or cls.__name__
#         cls._stage = stage

#     @classmethod
#     def defaults(cls, **params):
#         return C(
#             title=cls.__name__,
#             step_name=cls._identifier
#         )


# class Stage(object):
#     def __init_subclass__(cls, title, key=None, order=0):
#         cls.__identifier__ = key or cls.__name__
#         cls.__title__ = cls.__title__
#         cls.__order__ = order

#     def record(self, process_id):
#         return SimpleNamespace(
#             _id=UUID_GENF(cls.__identifier__, process_id),
#             process_id=process_id,
#             key=cls.__identifier__,
#             title=self.__title__,
#             desc=self.__doc__,
#             order=cls.__order__
#         )


# def _is_stage(ele):
#     if not ele:
#         return False

#     return issubclass(ele, Stage)


# def _is_step(ele):
#     if not ele:
#         return False

#     return issubclass(ele, WorkflowStep)


# class Workflow(object):
#     __key__         = None
#     __title__       = None
#     __revision__    = 0
#     __namespace__   = None

#     _step_cls   = {}
#     _stages     = {}
#     _roles      = {}

#     def __init__(self, instance: WorkflowInstance):
#         self._data = instance

#     @property
#     def data(self):
#         return self._data

#     @property
#     def _id(self):
#         return self._data._id

#     def __init_subclass__(cls, key, title, revision=0, namespace=None):
#         cls.__key__ = camel_to_lower(getattr(cls, '__key__', None) or cls.__name__)

#         cls._step_cls = cls._step_cls.copy()
#         cls._stages = cls._stages.copy()

#         assert getattr(cls, '__title__', None), "Workflow must have a title set (__title__ = ...)"
#         assert getattr(cls, '__revision__', -1) >= 0, \
#             "Workflow must have a positive integer revision number (__revision__ = ...)"

#         def define_step(step_cls, stage=None):
#             key = step_cls._identifier
#             wf_name = cls._identifier
#             stage_name = stage or step_cls._stage

#             assert _is_step(step_cls)
#             if key in cls._step_cls:
#                 raise ValueError('Step already registered [%s]' % step_cls)

#             if stage_name not in cls._stages:
#                 raise ValueError('Stage [%s] is not defined for workflow [%s]' % (stage_name, wf_name))

#             step_cls._stage = stage_name
#             cls._step_cls[key] = step_cls

#             # Register step's external events listeners
#             EventRouter.register_events(step_cls, wf_name, step_name=key)

#         def define_stage(stage_cls):
#             assert _is_stage(stage_cls)
#             if not isinstance(stage_cls, WorkflowStage):
#                 stage_cls = stage_cls()

#             key = stage_cls._identifier or stage_cls.__name__
#             if key in cls._stages:
#                 raise ValueError('Stage already registered [%s]' % stage_cls)

#             cls._stages[key] = stage_cls

#             for attr in dir(stage_cls):
#                 step_cls = getattr(stage_cls, attr)
#                 if _is_step(step_cls):
#                     define_step(step_cls, stage=key)

#         for attr in dir(cls):
#             ele_cls = getattr(cls, attr)
#             if _is_stage(ele_cls):
#                 define_stage(ele_cls)
#                 continue

#             if _is_step(ele_cls):
#                 define_step(ele_cls)
#                 continue

#         EventRouter.register_events(cls, cls._identifier)

#     def on_created(self):
#         pass

#     def on_start(self):
#         pass

#     def on_terminated(self):
#         pass

#     def on_finished(self):
#         pass


# WorkflowRegistry = ClassRegistry(Workflow)


# '''
# class AbcdEFWorkflow(object):
#     __key__         = None
#     __title__       = None
#     __revision__    = 0
