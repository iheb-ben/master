import warnings

# Suppress the specific DeprecationWarning from jsonschema.RefResolver
warnings.filterwarnings('ignore', category=DeprecationWarning, module='jsonschema')

from . import test_auth
