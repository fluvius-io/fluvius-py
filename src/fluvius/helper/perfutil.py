import functools
from contextlib import contextmanager
from time import perf_counter
from pathlib import Path
from . import logger


class Timer(object):
    def __init__(self, label="_"):
        self.label = label

    def __enter__(self):
        logger.warning("TIMER START > %s ...", self.label)
        self.start = perf_counter()
        return self

    def __exit__(self, *args):
        self.interval = perf_counter() - self.start
        logger.warning("TIMER FINISH> %s [%07.9fs elapsed]" % (self.label, self.interval))
        return self


def _perf_decorator(func, args, context, generator=True, asyncgen=True, coroutine=True):
    import inspect
    ctx_args = args

    if inspect.isgeneratorfunction(func):
        assert generator, "Generator function is not supported by [%s]" % str(context)

        @functools.wraps(func)
        def generator_wrapper(*args, **kwargs):
            with context(*ctx_args):
                yield from func(*args, **kwargs)
        return generator_wrapper

    if inspect.isasyncgenfunction(func):
        assert asyncgen, "Generator function is not supported by [%s]" % str(context)

        @functools.wraps(func)
        async def asyncgen_wrapper(*args, **kwargs):
            with context(*ctx_args):
                async for item in func(*args, **kwargs):
                    yield item
        return asyncgen_wrapper

    if inspect.iscoroutinefunction(func):
        assert coroutine, "Generator function is not supported by [%s]" % str(context)

        @functools.wraps(func)
        async def coroutine_wrapper(*args, **kwargs):
            with context(*ctx_args):
                return await func(*args, **kwargs)
        return coroutine_wrapper

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with context(*ctx_args):
            return func(*args, **kwargs)
    return wrapper


@contextmanager
def cprofile_context(fp, **profile_kwargs):
    import cProfile
    prof = cProfile.Profile()
    prof.enable()
    yield prof
    prof.disable()
    prof.dump_stats(fp, **profile_kwargs)


@contextmanager
def yappi_context(fp, **kwargs):
    import yappi
    yappi.start()
    yield yappi
    yappi.stop()
    with open(fp, "w") as f:
        fstats = yappi.get_func_stats()
        fstats.save(Path(fp).with_suffix(".pstat"), type="pstat")
        fstats.print_all(f)
        tstats = yappi.get_thread_stats()
        tstats.print_all(f)


@contextmanager
def pyinstrument_context(fp, **kwargs):
    from pyinstrument import Profiler
    profiler = Profiler()
    profiler.start()
    yield profiler
    profiler.stop()
    profiler.write_html(Path(fp).with_suffix(".html"))


def cprofile_profiler(filepath, disabled=False, **profile_kwargs):
    if disabled:
        return lambda func: func

    return functools.partial(
        _perf_decorator,
        args=(filepath,),
        context=cprofile_context,
        asyncgen=False,
        coroutine=False)


def yappi_profiler(filepath, disabled=False):
    if disabled:
        return lambda func: func

    return functools.partial(
        _perf_decorator,
        args=(filepath,),
        context=yappi_context
    )


def pyinstrument_profiler(filepath, disabled=False):
    if disabled:
        return lambda func: func

    return functools.partial(
        _perf_decorator,
        args=(filepath,),
        context=pyinstrument_context
    )


def timer(label, enabled=True):
    if not enabled:
        return lambda func: func

    return functools.partial(_perf_decorator, args=(label,), context=Timer)


def c_profiler(filepath, enabled=True, **profile_kwargs):
    if not enabled:
        return lambda func: func

    import cProfile
    import inspect

    def decorator(func):
        if inspect.isgeneratorfunction(func) or \
                inspect.isasyncgenfunction(func) or \
                inspect.iscoroutinefunction(func):
            raise ValueError(
                'c_profiler is not working properly with generator/async function. Use yappi_profiler instead.')

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            prof = cProfile.Profile()
            retval = prof.runcall(func, *args, **kwargs)
            # Note use of name from outer scope
            prof.dump_stats(filepath, **profile_kwargs)
            return retval
        return wrapper
    return decorator


def yappi_profiler(filepath, enabled=True):
    if not enabled:
        return lambda func: func

    import yappi
    import inspect
    from pathlib import Path

    @contextmanager
    def yappi_context(fp, **kwargs):
        yappi.start()
        yield yappi
        yappi.stop()
        with open(fp, "w") as f:
            fstats = yappi.get_func_stats()
            fstats.save(Path(fp).with_suffix(".pstat"), type="pstat")
            fstats.print_all(f)
            tstats = yappi.get_thread_stats()
            tstats.print_all(f)

    def decorator(func):
        if inspect.isgeneratorfunction(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                with yappi_context(filepath):
                    yield from func(*args, **kwargs)
        elif inspect.isasyncgenfunction(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                with yappi_context(filepath):
                    async for item in func(*args, **kwargs):
                        yield item
        elif inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                with yappi_context(filepath):
                    return await func(*args, **kwargs)
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                with yappi_context(filepath):
                    return func(*args, **kwargs)
        return wrapper
    return decorator
