# OpenCLIP
OpenCLIP is an advanced open-source implementation of the Contrastive Language-Image Pretraining (CLIP) model, originally developed by OpenAI. CLIP models are designed to learn visual concepts from natural language descriptions, enabling them to understand and generate associations between images and text.

OpenCLIP on GitHub 🤗:  
[OpenCLIP](https://github.com/mlfoundations/open_clip)

### Minimum Requirements
* 1x GPU_NV_S (1x NVIDIA A10G)

### 1. Run the General Setup
Make sure that you created all required databse objects from the general setup instructions [here](https://github.com/michaelgorkow/scs_llm_zoo/blob/main/README.md).

### 2. Build & Upload the container
```cmd
docker build build --platform linux/amd64 -t <ORGNAME>-<ACCTNAME>.registry.snowflakecomputing.com/llm_db/public/image_repository/en_clip_service:latest .  

docker push <ORGNAME>-<ACCTNAME>.registry.snowflakecomputing.com/llm_db/public/image_repository/en_clip_service:latest
```

### 3. Upload the Service Specification
You can use Snowflake's UI to upload the open_clip_spec.yml to @LLM_DB.PUBLIC.CONTAINER_FILES.  

### 4. Create the LLM Service
```sql
-- Create LLM service
CREATE SERVICE LLM_DB.PUBLIC.OPEN_CLIP_SERVICE
  IN COMPUTE POOL GPU_NV_S_POOL
  FROM @LLM_DB.PUBLIC.CONTAINER_FILES
  SPEC='open_clip_spec.yml'
  MIN_INSTANCES=1
  MAX_INSTANCES=1
  EXTERNAL_ACCESS_INTEGRATIONS = (LLM_ACCESS_INTEGRATION);

-- Verify Service is running
SELECT SYSTEM$GET_SERVICE_STATUS('OPEN_CLIP_SERVICE');
-- View Service Logs
SELECT SYSTEM$GET_SERVICE_LOGS('OPEN_CLIP_SERVICE',0,'open-clip-service-container');
```

### 5. Create the service function
```sql
-- Create the Service Functions
CREATE OR REPLACE FUNCTION LLM_DB.PUBLIC.OPEN_CLIP_ENCODE_TEXT(TEXT TEXT)
RETURNS ARRAY
SERVICE=LLM_DB.PUBLIC.OPEN_CLIP_SERVICE
ENDPOINT=API
AS '/encode_text';

CREATE OR REPLACE FUNCTION LLM_DB.PUBLIC.OPEN_CLIP_ENCODE_IMAGE(URL TEXT)
RETURNS ARRAY
SERVICE=LLM_DB.PUBLIC.OPEN_CLIP_SERVICE
ENDPOINT=API
AS '/encode_image';
```

### 6. Call the service functions
```sql
-- Simple inference for a single text
SELECT OPEN_CLIP_ENCODE_TEXT('Snowflake is a cool company!')::VECTOR(FLOAT, 768) AS EMBEDDING;

-- Calculate cosine similarity between text and image embeddings
SELECT 
    OPEN_CLIP_ENCODE_TEXT('Snowflake logo')::VECTOR(FLOAT, 768) AS EMB1, 
    OPEN_CLIP_ENCODE_TEXT('AWS logo')::VECTOR(FLOAT, 768) AS EMB2, 
    OPEN_CLIP_ENCODE_IMAGE('https://logos-world.net/wp-content/uploads/2022/11/Snowflake-Emblem.png')::VECTOR(FLOAT, 768) AS EMB3,
    OPEN_CLIP_ENCODE_IMAGE('https://upload.wikimedia.org/wikipedia/commons/thumb/9/93/Amazon_Web_Services_Logo.svg/2560px-Amazon_Web_Services_Logo.svg.png')::VECTOR(FLOAT, 768) AS EMB4,
    VECTOR_COSINE_SIMILARITY(EMB1, EMB3) AS EMB1_EMB3_SIM,
    VECTOR_COSINE_SIMILARITY(EMB1, EMB4) AS EMB1_EMB4_SIM,
    VECTOR_COSINE_SIMILARITY(EMB2, EMB3) AS EMB2_EMB3_SIM,
    VECTOR_COSINE_SIMILARITY(EMB2, EMB4) AS EMB2_EMB4_SIM;
```