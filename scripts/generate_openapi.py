import json
import sys
from pathlib import Path

# Add the parent directory (repository root) to the Python module search path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import app  # Import your app module

# Generate OpenAPI schema and save it to a file
with open("openapi.json", "w") as file:
    file.write(json.dumps(app.app.openapi_schema, indent=2))

print("OpenAPI schema successfully generated and saved to openapi.json.")
