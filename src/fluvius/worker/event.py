from blinker import signal

on_startup = signal("arq_worker_startup")
on_shutdown = signal("arq_worker_shutdown")
on_reload = signal("on_reload")

SANIC_HOOK_EVENT_MAP = {
    "before_server_start": on_startup,
    "after_server_start": on_startup,
    "before_server_stop": on_shutdown,
    "after_server_stop": on_shutdown,
}
