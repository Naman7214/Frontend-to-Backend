CODE_GENERATION_PROMPT = '''
# {project_name} - Full Codebase Generation

## Project Overview
Generate a complete Node.js Express REST API codebase for {project_name}.

## API Endpoints
{endpoints_json}

## Architecture Requirements
1. Use ES Module syntax (import/export) throughout, NOT CommonJS (require/module.exports)
2. Include .js extension in all import paths
3. Organize code with MVC pattern plus repositories:
   - routes/ - Route definitions
   - controllers/ - Request handlers
   - services/ - Business logic
   - models/ - Contains two folders:
       - schemas/ - Mongoose models
       - domains/ - Validation logic
   - repositories/ - Data access layer
   - middlewares/ - Auth, validation, error handling
   - utils/ - Helpers and utilities
   - config/ - Configuration
{auth_reference}
{db_reference}

## Files to Generate
Include the following files (and any others needed):
1. package.json - Include express, mongoose, dotenv, etc. with 'type': 'module'
2. .env - Environment variables
3. src/server.js - Entry point
4. src/app.js - Express setup
5. src/routes/ - All routes including index.js to combine routes
6. src/controllers/ - Controllers for each endpoint
7. src/models/ - Mongoose models for database entities
8. src/repositories/ - Data access code
9. src/middlewares/ - Auth, validation, error handling
10. src/services/ - Business logic
11. src/utils/ - Utility functions
12. src/models/domains - Request validation schemas, preferably using Joi
13. src/config/ - Configuration files (db.js, etc.)

## Output Format
Return a valid JSON array of objects with the following structure:
```json
[
  {{
    "file_path": "path/to/file.js",
    "code": "content of the file"
  }},
  ...
]
```

Ensure all files use consistent coding style and properly reference each other.
Do not include any explanations or markdown in your response, only the JSON array.
Ensure to use the same db_name mentioned in the endpoints.
''' 