import time
import mimetypes
import os
import requests
import signal
import threading
from datetime import datetime
from croniter import croniter
from enum import Enum
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from fluvius.error import BadRequestError
from fluvius.dmap.fetcher import DataFetcher
from fluvius.dmap.interface import InputFile
from fluvius.dmap import logger

STAGING_LOCATION = "/tmp"


class SafeSession:
    def __init__(self):
        self.session = requests.Session()
        self.lock = threading.Lock()

    def get(self, *args, **kwargs):
        with self.lock:
            return self.session.get(*args, **kwargs)

    def post(self, *args, **kwargs):
        with self.lock:
            return self.session.post(*args, **kwargs)


class RunMode(Enum):
    ONCE = 'once'
    INFINITE = 'infinite'


class RunStatus(Enum):
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"


@dataclass
class APIFetcherRequest:
    endpoint: str = None
    method: str = "GET"
    headers: dict = None
    params: dict = None
    data: dict = None

    def __post_init__(self):
        if not self.endpoint:
            raise BadRequestError(
                "T00.141",
                "Endpoint field must be set",
                None
            )

        self.params = self.params or {}
        self.headers = self.headers or {}


@dataclass
class APIFetcherConfig:
    name: str = "fetcher"
    max_threads: int = 10
    run_mode: str = 'infinite'
    request: APIFetcherRequest = None
    options: dict = None
    cron: str = "*/5 * * * *"

    def __post_init__(self):
        if self.request:
            self.request = APIFetcherRequest(**self.request)

        self.run_mode = RunMode(self.run_mode)
        self.options = self.options or {}

    def to_dict(self):
        return dict(
            name=self.name,
            max_threads=self.max_threads,
            run_mode=self.run_mode.value,
            options=self.options,
            cron=self.cron
        )

class APIFetcher(DataFetcher):
    name = "api"

    def validate_config(self, **config):
        return APIFetcherConfig(**config)

    def _is_stop_event(self):
        return self.stop_event.is_set()

    def _start_fetching(self):
        self.counter = 0
        self.stop_event = threading.Event()
        self.request_session = SafeSession()
        # signal.signal(signal.SIGINT, lambda s, f: self._signal_handler(s, f))

    def _stop_fetching(self):
        self.stop_event.set()

    def _signal_handler(self, signal, frame):
        """Handle Ctrl+C to stop fetching gracefully."""
        logger.info("Graceful shutdown initiated...")
        self._stop_fetching()

    def _handle_request(self, request: APIFetcherRequest):
        if not isinstance(request, APIFetcherRequest):
            raise BadRequestError(
                "T00.142",
                "[request] argument must be instances of class APIFetcherRequest",
                None
            )

        if request.method.upper() == "GET":
            return self.request_session.get(url=request.endpoint, headers=request.headers, params=request.params)
        elif request.method.upper() == "POST":
            return self.request_session.post(url=request.endpoint, headers=request.headers, params=request.params, data=request.data)
        else:
            raise BadRequestError(
                "T00.143",
                f"{request.method} is not supported!",
                None
            )

    def _handle_response(self, request, response: requests.Response):
        def _detect_extension():
            content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
            return mimetypes.guess_extension(content_type) or ""

        response.raise_for_status()
        extension = _detect_extension()
        context = {"request": request}

        data = self.on_response(context, response)

        file_name = "{}-{}-{}{}".format(
            datetime.utcnow(),
            self.config.name,
            f"{self.counter + 1:0>6}",
            extension
        )

        file_path = os.path.join(STAGING_LOCATION, file_name)
        with open(file_path, "wb") as temp_file:
            temp_file.write(data)

        return file_path

    def on_response(self, context, response):
        # Note: Each fetcher can custom response and return binary data
        return response.content

    def on_request(self):
        if not self.config.request:
            raise NotImplementedError("The on_request method is not implemented or self.config.request is not set ...")

        return [self.config.request]

    def on_notify(self, status):
        pass

    def fetch(self):
        self._start_fetching()
        self.counter = 0

        cron_expr = self.config.cron
        cron_iter = croniter(cron_expr, datetime.utcnow())
        next_run = cron_iter.get_next(datetime)
        logger.info("Next fetching: %s" % next_run)

        with ThreadPoolExecutor(max_workers=self.config.max_threads) as executor:

            while not self._is_stop_event():
                status = RunStatus.SUCCESS

                current_time = datetime.utcnow()
                if self.config.run_mode == RunMode.ONCE or current_time >= next_run:
                    next_run = cron_iter.get_next(datetime)

                    try:
                        logger.info(f"Fetching {self.counter}")

                        futures = {}
                        for request in self.on_request():
                            future = executor.submit(self._handle_request, request)
                            futures[future] = request

                        for completed_future in as_completed(futures):
                            req = futures[completed_future]
                            try:
                                response = completed_future.result()
                                filepath = self._handle_response(req, response)
                                yield InputFile.from_file(filepath)

                            except Exception as e:
                                logger.error(f"Error during fetching: {e}")
                                continue

                            self.counter += 1

                        if self.config.run_mode == RunMode.ONCE:
                            break

                        logger.info("Next fetching: %s" % next_run)
                    except Exception as e:
                        logger.error(f"Error during fetching: {e}")
                        status = RunStatus.ERROR
                        self._stop_fetching()

                    self.on_notify(status)

                time.sleep(1) # avoid high CPU usage

            if not self.counter:
                logger.error("No files were successfully fetched from the provided API endpoints.")
                return
