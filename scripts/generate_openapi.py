import json

import app

# Generate OpenAPI schema and save it to a file
with open("openapi.json", "w") as file:
    file.write(json.dumps(app.app.openapi_schema, indent=2))

print("OpenAPI schema successfully generated and saved to openapi.json.")
