import traceback
from typing import Optional
from ._meta import config, logger


class ErrorTracker:
    """Base class for error tracking implementations.
    
    Subclasses are automatically registered via __init_subclass__.
    Use capture_exception() to capture exceptions.
    """
    
    _REGISTRY = {}
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        key = cls.__name__
        if key in cls._REGISTRY:
            raise ValueError(f"Error tracker is already registered: {key} => {cls._REGISTRY[key]}")
        
        cls._REGISTRY[key] = cls
        logger.info(f"Registered error tracker: {key}")
    
    def capture_exception(self, exception: Exception, **kwargs):
        raise NotImplementedError("Subclasses must implement capture_exception")
    
    @classmethod
    def get_tracker(cls, name: str, **kwargs) -> 'ErrorTracker':
        """Get a tracker instance by name."""
        if name not in cls._REGISTRY:
            raise ValueError(f"Error tracker not found: {name}")
        
        return cls._REGISTRY[name](**kwargs)


class NullTracker(ErrorTracker):
    """A no-op tracker that does nothing."""
    
    def capture_exception(self, exception: Exception, **kwargs):
        logger.info("NullTracker: Exception captured (no action taken): %s", exception)


class PosthogTracker(ErrorTracker):
    """Posthog error tracker implementation."""
    
    def __init__(self):
        super().__init__()
        try:
            from posthog import Posthog
            self.posthog = Posthog(
                config.POSTHOG_API_KEY,
                host=config.POSTHOG_HOST,
                enable_exception_autocapture=True
            )
            logger.info("Posthog tracker initialized")
        except ImportError:
            logger.warning("Posthog not installed. Install with: pip install posthog")
            self.posthog = None
        except Exception as e:
            logger.error("Failed to initialize Posthog tracker: %s", e)
            self.posthog = None
    
    def capture_exception(self, exception: Exception, **kwargs):
        if self.posthog is None:
            return
        
        try:
            properties = {
                "exception_type": type(exception).__name__,
                "exception_message": str(exception),
                "exception_traceback": traceback.format_exc(),
            }
            
            self.posthog.capture_exception(
                exception,
                properties=properties
            )
        except Exception as e:
            logger.error("Failed to capture exception in Posthog: %s", e)


class SentryTracker(ErrorTracker):
    """Sentry error tracker implementation."""
    
    def __init__(self, dsn: Optional[str] = None):
        super().__init__()
        self.dsn = dsn or getattr(config, "SENTRY_DSN", None)
        
        if not self.dsn:
            logger.warning("Sentry DSN not configured. Set SENTRY_DSN in config.")
            self.sentry = None
            return
        
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.asyncio import AsyncioIntegration
            
            sentry_sdk.init(
                dsn=self.dsn,
                integrations=[
                    FastApiIntegration(),
                    AsyncioIntegration(),
                ],
                traces_sample_rate=1.0,
            )
            self.sentry = sentry_sdk
            logger.info("Sentry tracker initialized")
        except ImportError:
            logger.warning("Sentry SDK not installed. Install with: pip install sentry-sdk")
            self.sentry = None
        except Exception as e:
            logger.error("Failed to initialize Sentry tracker: %s", e)
            self.sentry = None
    
    def capture_exception(self, exception: Exception, **kwargs):
        """Capture exception in Sentry.
        
        Args:
            exception: The exception to capture
            **kwargs: Additional context to include with the exception
        """
        if self.sentry is None:
            return
        
        try:
            if kwargs:
                with self.sentry.push_scope() as scope:
                    for key, value in kwargs.items():
                        scope.set_extra(key, value)
                    self.sentry.capture_exception(exception)
        except Exception as e:
            logger.error("Failed to capture exception in Sentry: %s", e)

