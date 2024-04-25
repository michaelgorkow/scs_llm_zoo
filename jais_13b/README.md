# Jais-13b-chat
The Jais-13b-chat is a 13 billion parameter bilingual large language model fine-tuned for both Arabic and English. It utilizes a transformer-based decoder-only (GPT-3) architecture and features SwiGLU non-linearity. The model includes ALiBi position embeddings, enhancing its ability to manage longer sequence lengths, thus improving context handling and precision.

This model is an advanced version of Jais-13b, which has been fine-tuned using a curated set of 4 million Arabic and 6 million English prompt-response pairs. The developers have further refined the model with safety-oriented instructions and added extra protective measures through a safety prompt. The base model, Jais-13b, was initially trained on a massive dataset comprising 116 billion Arabic tokens and 279 billion English tokens.

Thanks to the largest curated dataset of Arabic and English instructions for tuning, combined with the capability for multi-turn conversations, the model excels in engaging in a variety of topics, especially those relevant to the Arab world.

Repository on Hugging Face 🤗:  
[core42/jais-13b-chat](https://huggingface.co/core42/jais-13b-chat)

### Minimum Requirements
* 1x GPU_NV_M (4x NVIDIA A10G)

### 1. Run the General Setup
Make sure that you created all required databse objects from the general setup instructions [here](https://github.com/michaelgorkow/scs_llm_zoo/blob/main/README.md).

### 2. Build & Upload the container
Feel free to use any one the provided container images.  
Just make sure that the image name in your spec.yml file is the same as the one you use for building and uploading the image.  
This example code assumes an image called `llm_service`.
```cmd
docker build -t <ORGNAME>-<ACCTNAME>.registry.snowflakecomputing.com/llm_db/public/image_repository/jais_13b_service:latest .
docker push <ORGNAME>-<ACCTNAME>.registry.snowflakecomputing.com/llm_db/public/image_repository/jais_13b_service:latest
```

### 3. Upload the Service Specification
You can use Snowflake's UI to upload the jais_13b_spec.yml to @LLM_DB.PUBLIC.CONTAINER_FILES.  

### 4. Create the LLM Service
```sql
-- Create Jais 13B service
CREATE SERVICE LLM_DB.PUBLIC.JAIS_13B_SERVICE
  IN COMPUTE POOL LLM_GPU_POOL_MEDIUM
  FROM @LLM_DB.PUBLIC.CONTAINER_FILES
  SPEC='jais_13b_spec.yml'
  MIN_INSTANCES=1
  MAX_INSTANCES=1
  EXTERNAL_ACCESS_INTEGRATIONS = (LLM_ACCESS_INTEGRATION);

-- Verify Service is running
SELECT SYSTEM$GET_SERVICE_STATUS('JAIS_13B_SERVICE');
-- View Service Logs
SELECT SYSTEM$GET_SERVICE_LOGS('JAIS_13B_SERVICE',0,'jais-13b-service-container');
```

### 5. Create the service functions
```sql
-- Create service function
CREATE OR REPLACE FUNCTION LLM_DB.PUBLIC.JAIS_13B_COMPLETE(INPUT_PROMPT TEXT, INPUT_LANG TEXT)
RETURNS TEXT
SERVICE=LLM_DB.PUBLIC.JAIS_13B_SERVICE
ENDPOINT=API
AS '/complete';
```

### 6. Call the service functions
```sql
-- Ask questions in Arabic
SELECT LLM_DB.PUBLIC.JAIS_13B_COMPLETE('ما هي عاصمة الامارات؟', 'AR') AS RESPONSE;
-- Response: العاصمة الإماراتية أبو ظبي
-- Ask questions in English
SELECT LLM_DB.PUBLIC.JAIS_13B_COMPLETE('What is the capital of UAE?', 'EN') AS RESPONSE;
--  Response: The capital city of the United Arab Emirates (UAE) is Abu Dhabi.
```