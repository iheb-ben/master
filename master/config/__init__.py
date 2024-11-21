from master.tools.misc import temporairy_directory
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from pathlib import Path
import sys

# Current system version
version = 1

from . import parser
from . import logging


def system_directory() -> Path:
    """
    Determines the system's directory for storing files.
    - If the configuration includes a `store_folder` key, its value is used as the directory.
    - If `store_folder` is not set, a temporary directory is used instead.
    Returns:
        Path: The path to the storage directory.
    """
    store_folder = parser.arguments.configuration.get('store_folder', None)
    if not store_folder:
        store_folder = str(temporairy_directory())
    return Path(store_folder)


def default_keys_location() -> Path:
    """
    Determines the default location for storing key files based on the current configuration.
    If the 'pipeline' configuration is enabled, the folder is named 'master_keys';
    otherwise, it's named 'node_keys'. The folder is created in a temporary directory
    if it does not already exist.
    Returns:
        pathlib.Path: The path to the folder where keys should be stored.
    """
    folder_name = 'node_keys'
    if parser.arguments.configuration['pipeline']:
        folder_name = 'master_keys'
    directory_path = system_directory().joinpath(folder_name)
    if not directory_path.exists():
        directory_path.mkdir()
    return directory_path


def rename_file_if_exists(file_path: Path):
    """
    Renames the given file to avoid overwriting, using a unique name in the same directory.
    Args:
        file_path (Path): The file to rename.
    """
    if file_path.exists():
        count = 1
        while True:
            new_name = file_path.with_name(f"{file_path.stem}_old_{count}{file_path.suffix}")
            if not new_name.exists():
                file_path.rename(new_name)
                break
            count += 1


_logger = logging.get_logger(__name__)


def configure_system():
    """
    Configures the system by ensuring consistency between RSA private and public keys.
    - If only the private key exists, regenerates the public key from it.
    - If only the public key exists, renames it and recreates both keys.
    - If neither key exists, generates and saves both keys.
    - If both keys exist, does nothing.
    """
    if parser.arguments.show_helper():
        sys.exit(1)
    _logger.info(f"Master Password: {parser.arguments.configuration['master_password']}")
    parser.arguments.save_configuration()
    key_location = default_keys_location()
    private_key_path = key_location.joinpath('private_key.pem')
    public_key_path = key_location.joinpath('public_key.pem')
    if private_key_path.exists() and not public_key_path.exists():
        # Load the private key and regenerate the public key
        with open(private_key_path, 'rb') as private_file:
            private_key = serialization.load_pem_private_key(private_file.read(), password=None)
        public_key = private_key.public_key()
        with open(public_key_path, 'wb') as public_file:
            public_file.write(public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))
    elif public_key_path.exists() and not private_key_path.exists():
        # Rename the public key and regenerate both keys
        rename_file_if_exists(public_key_path)
        generate_keys(private_key_path, public_key_path)
    elif not private_key_path.exists() and not public_key_path.exists():
        # Generate both keys
        generate_keys(private_key_path, public_key_path)


def generate_keys(private_key_path: Path, public_key_path: Path):
    """
    Generates a new RSA key pair and saves them to the specified paths.
    Args:
        private_key_path (Path): The file path to save the private key.
        public_key_path (Path): The file path to save the public key.
    """
    # Generate private (secret) key
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    # Generate public key from private key
    public_key = private_key.public_key()
    # Save private key to a PEM file
    with open(str(private_key_path), 'wb') as private_file:
        private_file.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    # Save public key to a PEM file
    with open(str(public_key_path), 'wb') as public_file:
        public_file.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))
