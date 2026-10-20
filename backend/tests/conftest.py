import sys
import os

# Automatically add the backend directory to sys.path so 'app' is always discoverable
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Ensure sample farmers are available for unit test assertions
os.environ["SEED_DEMO_FARMERS"] = "true"
