import logging
import logging.config
import os


class Logger:
    """A Singleton class to set up and manage logging for the application."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._setup_logger()
        return cls._instance

    def _setup_logger(self):
        """
        Sets up the logger configuration. This includes loading settings
        from a configuration file if available, and falling back to default settings if not.
        """
        log_config_file = os.path.join(os.path.dirname(__file__), "logger.conf")

        if os.path.exists(log_config_file):
            # If a logging configuration file is found, load settings from it
            logging.config.fileConfig(log_config_file)
        else:
            # Fallback: Set up a default basic logger configuration
            log_level = "INFO"

            logging.basicConfig(
                level=log_level,  # Set the logging level
                format="%(asctime)s - %(levelname)s - %(message)s",  # Log format
                handlers=[
                    logging.StreamHandler(),  # Output logs to the console
                    logging.FileHandler(
                        "application.log", mode="a"
                    ),  # Output logs to a file
                ],
            )

        self.logger = logging.getLogger()

        # Adjust log level if set in the environment
        log_level = os.getenv("LOG_LEVEL")
        if log_level:
            log_level = log_level.upper()
            self.logger.setLevel(log_level)
            self.logger.info(f"Logger level set to {log_level}")

    def get_logger(self, log_level=None):
        """
        Returns the configured logger instance.

        Returns:
        --------
        logger: logging.Logger
            The configured logger instance.
        """
        if log_level:
            self.logger.setLevel(log_level)

        return self.logger
