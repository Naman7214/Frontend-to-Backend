DATABASE_SCHEMA_USER_PROMPT = """
    Analyze the following API endpoint details and determine the appropriate database schema:
    
    Endpoint: {endpointName}
    Method: {method}
    Description: {description}
    
    Request Payload:
    {payload}
    
    Response Structure:
    {response}
    
    Based on this information, please:
    
    1. Identify the most appropriate MongoDB collection name for this endpoint (use naming conventions like 'users', 'products', etc.)
    2. Determine the schema structure with field names and their data types
    3. Generate sample values for each field that would be appropriate for testing
    4. The data types should be in the format of mongoDB data types (e.g., string, integer, boolean, date, etc.)
    
    Return the result in the following JSON format:
    {{
        "collection_name": "string",
        "schema": {{
            "field_name": "data_type"
            // Example: "username": "string", "age": "integer"
        }},
        "samples": {{
            "field_name": "sample_value"
        }}
    }}
    
    Important: If this endpoint appears to belong to the same collection as a previously analyzed endpoint, 
    please use the same collection name. For example, user authentication endpoints like signin, signup, etc., 
    should all use the same 'users' collection.
    """

DATABASE_SCHEMA_SYSTEM_PROMPT = "You are a helpful assistant that analyzes API endpoints and suggests database schemas."
