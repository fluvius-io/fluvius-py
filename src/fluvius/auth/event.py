from blinker import signal

factory_setup = signal("fluvius_auth__factory_setup")
endpoint_setup = signal("fluvius_auth__endpoint_setup")

authorization_success = signal("fluvius_auth__authorization_success")
authorization_failed = signal("fluvius_auth__authorization_failed")
authorization_start = signal("fluvius_auth__authorization_start")
user_logout = signal("fluvius_auth__user_logout")
