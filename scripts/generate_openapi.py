import json
import sys
from pathlib import Path

# Add the parent directory (repository root) to the Python module search path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import app  # Import your Litestar app instance

# Convert the OpenAPI schema to a dictionary
openapi_schema_dict = app.app.openapi_schema.to_schema()

# Save the OpenAPI schema as a JSON file
with open("../openapi.json", "w") as file:
    for path, methods in openapi_schema_dict.get("paths", {}).items():
        for method, details in methods.items():
            if isinstance(details, dict):
                parameters = details.get("parameters", [])
                for param in parameters:
                    if param.get("in") == "path":
                        param.pop("allowEmptyValue", None)
                        param.pop("allowReserved", None)
    file.write(json.dumps(openapi_schema_dict, indent=2))

print("OpenAPI schema successfully generated and saved to openapi.json.")

