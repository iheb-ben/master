from typing import Optional
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from pathlib import Path
import sys
import logging

from master.core import arguments
from master.core.parser import PipelineMode
from master.tools.paths import temporairy_directory

_logger = logging.getLogger(__name__)


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
    if arguments['pipeline_mode'] == PipelineMode.MANAGER.value:
        folder_name = 'master_keys'
    directory_path = Path(arguments['directory']) / folder_name
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


private_key_path: Optional[Path] = None
public_key_path: Optional[Path] = None


def configure():
    """
    Configures the system by ensuring consistency between RSA private and public keys.

    - If only the private key exists, regenerates the public key from it.
    - If only the public key exists, renames it and recreates both keys.
    - If neither key exists, generates and saves both keys.
    - If both keys exist, does nothing.
    """
    global private_key_path, public_key_path
    key_location = default_keys_location()
    private_key_path = key_location / 'private_key.pem'
    public_key_path = key_location / 'public_key.pem'
    if private_key_path.exists() and not public_key_path.exists():
        _logger.debug('Load the private key and regenerate the public key')
        with open(private_key_path, 'rb') as private_file:
            private_key = serialization.load_pem_private_key(private_file.read(), password=None)
        public_key = private_key.public_key()
        with open(public_key_path, 'wb') as public_file:
            public_file.write(public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))
    elif public_key_path.exists() and not private_key_path.exists():
        _logger.debug('Rename the current public key and regenerate both keys')
        rename_file_if_exists(public_key_path)
        generate_keys()
    elif not private_key_path.exists() and not public_key_path.exists():
        generate_keys()
    elif not is_public_key_valid():
        _logger.debug('Invalid keys found, rename both keys')
        rename_file_if_exists(private_key_path)
        rename_file_if_exists(public_key_path)
        generate_keys()
    else:
        _logger.debug(f'Public key in path: "{public_key_path}"')


def generate_keys():
    """
    Generates a new RSA key pair and saves them to the specified paths.
    """
    # Generate private (secret) key
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    # Generate public key from private key
    public_key = private_key.public_key()
    # Save private key to a PEM file
    with open(private_key_path, 'wb') as private_file:
        private_file.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    # Save public key to a PEM file
    with open(public_key_path, 'wb') as public_file:
        public_file.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))
    _logger.debug(f'Generated new public key in path: "{public_key_path}"')


# noinspection PyBroadException
def is_public_key_valid() -> bool:
    """
    Validates if a given public key corresponds to the private key in the provided path.
    Returns:
        bool: True if the public key matches the private key, False otherwise.
    """
    try:
        # Load private key
        with open(private_key_path, 'rb') as priv_file:
            private_key = serialization.load_pem_private_key(priv_file.read(), password=None)
        # Load public key
        with open(public_key_path, 'rb') as publ_file:
            public_key = serialization.load_pem_public_key(publ_file.read())
        # Test the key pair by signing and verifying a message
        test_message = b"test message"
        signature = private_key.sign(
            test_message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        # Verify the signature with the public key
        public_key.verify(
            signature,
            test_message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except Exception:
        return False
