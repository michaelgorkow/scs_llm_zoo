# GLM-4V-9B
GLM-4-9B is an open-source model from the latest GLM-4 series developed by Zhipu AI. This model, GLM-4V-9B, excels in dialogue capabilities in both Chinese and English with a high resolution of 1120x1120. It outperforms other models, such as GPT-4-turbo-2024-04-09, Gemini 1.0 Pro, Qwen-VL-Max, and Claude 3 Opus, in various multimodal evaluations. These evaluations encompass a wide range of abilities, including proficiency in Chinese and English, perception and reasoning, text recognition, and chart understanding. Additionally, this generation of models supports 26 languages, including Japanese, Korean, and German, enhancing its multilingual capabilities.

Repository on Hugging Face 🤗:  
[THUDM/glm-4v-9b](https://huggingface.co/THUDM/glm-4v-9b/blob/main/README_en.md)

### Minimum Requirements
* 1x GPU_NV_S (1x NVIDIA A10G)

We are loading with `load_in_4bit` enabled to reduce memory and computational costs by representing weights and activations with lower-precision data types.
This flag enables 4-bit quantization by replacing the Linear layers with FP4/NF4 layers from bitsandbytes. 
Without this flag, this model would not fit on a single NVIDIA A10G.

### 1. Run the General Setup
Make sure that you created all required databse objects from the general setup instructions [here](https://github.com/michaelgorkow/scs_llm_zoo/blob/main/README.md).

### 2. Build & Upload the container
```cmd
docker build build --platform linux/amd64 -t <ORGNAME>-<ACCTNAME>.registry.snowflakecomputing.com/llm_db/public/image_repository/glm_4v_9b_service:latest .
docker push <ORGNAME>-<ACCTNAME>.registry.snowflakecomputing.com/llm_db/public/image_repository/glm_4v_9b_service:latest
```

### 3. Upload the Service Specification
You can use Snowflake's UI to upload the glm_4v_9b_spec.yml to @LLM_DB.PUBLIC.CONTAINER_FILES.  

### 4. Create the LLM Service
```sql
-- Create LLM service
CREATE SERVICE LLM_DB.PUBLIC.GLM_V4_9B_SERVICE
  IN COMPUTE POOL LLM_GPU_POOL_SMALL
  FROM @LLM_DB.PUBLIC.CONTAINER_FILES
  SPEC='glm_4v_9b_spec.yml'
  MIN_INSTANCES=1
  MAX_INSTANCES=1
  EXTERNAL_ACCESS_INTEGRATIONS = (LLM_ACCESS_INTEGRATION);

-- Verify Service is running
SELECT SYSTEM$GET_SERVICE_STATUS('GLM_V4_9B_SERVICE');
-- View Service Logs
SELECT SYSTEM$GET_SERVICE_LOGS('GLM_V4_9B_SERVICE',0,'glm-4v-9b-service-container');
```

### 5. Create the service functions
```sql
-- Create service function (text only)
CREATE OR REPLACE FUNCTION LLM_DB.PUBLIC.GLM_V4_9B_COMPLETE(INPUT_PROMPT TEXT, GENERATION_ARGS OBJECT)
RETURNS TEXT
SERVICE=LLM_DB.PUBLIC.GLM_V4_9B_SERVICE
ENDPOINT=API
AS '/complete';

-- Create service function that supports an image url
CREATE OR REPLACE FUNCTION LLM_DB.PUBLIC.GLM_V4_9B_COMPLETE_IMAGE(INPUT_PROMPT TEXT, GENERATION_ARGS OBJECT, IMAGE_URL TEXT)
RETURNS TEXT
SERVICE=LLM_DB.PUBLIC.GLM_V4_9B_SERVICE
ENDPOINT=API
AS '/complete_image';
```

### 6. Call the service functions
```sql
-- Chat with with default settings:
SELECT LLM_DB.PUBLIC.GLM_V4_9B_COMPLETE(
    'Generate the next 3 numbers for this Fibonacci sequence: 0, 1, 1, 2.', 
    object_construct('max_length',2500,'top_k',1,'top_p',0.8,'temperature',0.8)) AS RESPONSE;

-- Query the LLM with an Image from a Snowflake stage
SELECT LLM_DB.PUBLIC.GLM_V4_9B_COMPLETE_IMAGE(
    'Who is this?', 
    object_construct('max_length',2500,'top_k',1,'top_p',0.8,'temperature',0.8), 
    GET_PRESIGNED_URL('@IMAGE_FILES', 'obama.jpg'));

-- Query the LLM with images from a Snowflake stage using a Directory table
SELECT LLM_DB.PUBLIC.GLM_V4_9B_COMPLETE_IMAGE(
    'Who is this?', 
    object_construct('max_length',2500,'top_k',1,'top_p',0.8,'temperature',0.8), 
    GET_PRESIGNED_URL('@IMAGE_FILES', RELATIVE_PATH))
FROM DIRECTORY('@IMAGE_FILES');
```

### 7. Streamlit Apps
The folder streamlit_app provides code for a Streamlit in Snowflake (SiS) App.  
This app provides a simple UI to query the LLM in three different ways:  
1. A simple text-only query
2. Query images from a stage in Snowflake (must have Directory Table enabled)
3. Query images from a given URL

It's not yet officially supported to connect to your container services from within a SiS app.
For that reason, the container itself hosts a Streamlit app which can be reached via its endpoint.  
You can find the streamlit endpoint endpoint by running:
```sql
SHOW ENDPOINTS IN SERVICE LLM_DB.PUBLIC.GLM_V4_9B_SERVICE;
```
This app has two two main differences:  
* It supports streamed responses
* It allows uploading local files

### 8. Demo
