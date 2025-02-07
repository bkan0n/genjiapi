import json
import sys
from pathlib import Path

# Add the parent directory (repository root) to the Python module search path
sys.path.append(str(Path(__file__).resolve().parent.parent))


import app  # Import your Litestar app instance

# Convert the OpenAPI schema to a dictionary
openapi_schema_dict = app.app.openapi_schema.to_schema()

# Save the OpenAPI schema as a JSON file
with open("openapi.json", "w") as file:
    file.write(json.dumps(openapi_schema_dict, indent=2))

print("OpenAPI schema successfully generated and saved to openapi.json.")
