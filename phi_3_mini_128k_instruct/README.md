# Phi-3-Mini-128K-Instruct
The Phi-3-Mini-128K-Instruct is a 3.8 billion-parameter, lightweight, state-of-the-art open model trained using the Phi-3 datasets.  
This dataset includes both synthetic data and filtered publicly available website data, with an emphasis on high-quality and reasoning-dense properties.  
The model belongs to the Phi-3 family with the Mini version in two variants 4K and 128K which is the context length (in tokens) that it can support.  

Repository on Hugging Face 🤗:  
[microsoft/Phi-3-mini-128k-instruct](https://huggingface.co/microsoft/Phi-3-mini-128k-instruct)

### Minimum Requirements
* 1x GPU_NV_S (1x NVIDIA A10G)

### 1. Run the General Setup
Make sure that you created all required databse objects from the general setup instructions [here](https://github.com/michaelgorkow/scs_llm_zoo/blob/main/README.md).

### 2. Build & Upload the container
```cmd
docker build -t <ORGNAME>-<ACCTNAME>.registry.snowflakecomputing.com/llm_db/public/image_repository/phi_3_mini_128k_instruct_service:latest .
docker push <ORGNAME>-<ACCTNAME>.registry.snowflakecomputing.com/llm_db/public/image_repository/phi_3_mini_128k_instruct_service:latest
```

### 3. Upload the Service Specification
You can use Snowflake's UI to upload the phi_3_mini_128k_instruct_spec.yml to @LLM_DB.PUBLIC.CONTAINER_FILES.  

### 4. Create the LLM Service
```sql
-- Create Jais 13B service
CREATE SERVICE LLM_DB.PUBLIC.PHI_3_MINI_128K_INSTRUCT_SERVICE
  IN COMPUTE POOL LLM_GPU_POOL_SMALL
  FROM @LLM_DB.PUBLIC.CONTAINER_FILES
  SPEC='phi_3_mini_128k_instruct_spec.yml'
  MIN_INSTANCES=1
  MAX_INSTANCES=1
  EXTERNAL_ACCESS_INTEGRATIONS = (LLM_ACCESS_INTEGRATION);

-- Verify Service is running
SELECT SYSTEM$GET_SERVICE_STATUS('PHI_3_MINI_128K_INSTRUCT_SERVICE');
-- View Service Logs
SELECT SYSTEM$GET_SERVICE_LOGS('PHI_3_MINI_128K_INSTRUCT_SERVICE',0,'phi-3-mini-128k-service-container');
```

### 5. Create the service functions
```sql
-- Create service function
CREATE OR REPLACE FUNCTION LLM_DB.PUBLIC.PHI_3_MINI_128K_INSTRUCT_COMPLETE(INPUT_PROMPT TEXT)
RETURNS TEXT
SERVICE=LLM_DB.PUBLIC.PHI_3_MINI_128K_INSTRUCT_SERVICE
ENDPOINT=API
AS '/complete';

-- Create service function for custom function
CREATE OR REPLACE FUNCTION LLM_DB.PUBLIC.PHI_3_MINI_128K_INSTRUCT_COMPLETE_CUSTOM(SYSTEM_PROMPT TEXT, INPUT_PROMPT TEXT, MAX_NEW_TOKENS INT, TEMPERATURE FLOAT)
RETURNS TEXT
SERVICE=LLM_DB.PUBLIC.PHI_3_MINI_128K_INSTRUCT_SERVICE
ENDPOINT=API
AS '/complete_custom';
```

### 6. Call the service functions
```sql
-- Chat with with default settings:
SELECT LLM_DB.PUBLIC.PHI_3_MINI_128K_INSTRUCT_COMPLETE('Generate the next 3 numbers for this Fibonacci sequence: 0, 1, 1, 2.') AS RESPONSE;
-- Define system_prompt, max_token, temperature and top_p yourself:
SELECT LLAMA3.PUBLIC.PHI_3_MINI_128K_INSTRUCT_COMPLETE_CUSTOM(
    'You are a coding assistant for Python. Only return Python code.', 
    'Write Python code to generate the fibonacci sequence.', 
    500, 
    0.0) AS RESONSE;
```