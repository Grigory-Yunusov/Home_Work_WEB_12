#src.conf.consig.py

"""
Configuration Module.

This module contains the Settings class, which is used to load configuration
values from environment variables or a .env file. It uses the pydantic_settings
library to define the settings and load them from a .env file.
"""

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Settings class for application configuration.

    This class uses pydantic_settings to define settings that are loaded from
    environment variables or a .env file. The following settings are defined:

    - sqlalchemy_database_url: The URL for the SQLAlchemy database connection.
    - secret_key: The secret key for JWT encoding and decoding.
    - algorithm: The algorithm used for JWT encoding and decoding.
    - mail_username: The username for the email server.
    - mail_password: The password for the email server.
    - mail_from: The email address to send emails from.
    - mail_port: The port for the email server.
    - mail_server: The email server address.
    - redis_host: The host for the Redis server.
    - redis_port: The port for the Redis server.
    - postgres_db: The name of the PostgreSQL database.
    - postgres_user: The username for the PostgreSQL database.
    - postgres_password: The password for the PostgreSQL database.
    - postgres_port: The port for the PostgreSQL database.
    - cloudinary_name: The name of the Cloudinary account.
    - cloudinary_api_key: The API key for Cloudinary.
    - cloudinary_api_secret: The API secret for Cloudinary.

    The settings are loaded from a .env file located in the root of the project.
    """
    sqlalchemy_database_url: str="postgresql+psycopg2://POSTGRES_USER:POSTGRES_PASSWORD@localhost:5432/POSTGRES_DB"
    secret_key: str="test"
    algorithm: str="test"
    mail_username: str="test"
    mail_password: str="test"
    mail_from: str="test"
    mail_port: int=1
    mail_server: str="test"
    redis_host: str ="test"
    redis_port: int=1
    postgres_db: str ="test"
    postgres_user: str ="test"
    postgres_password: str ="test"
    postgres_port: int = 5432 
    cloudinary_name: str="test"
    cloudinary_api_key: str="test"
    cloudinary_api_secret: str="test"

    class Config:
        """
        Configuration class for pydantic_settings.

        This class specifies the .env file to load settings from and the encoding
        of the .env file.
        """
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
