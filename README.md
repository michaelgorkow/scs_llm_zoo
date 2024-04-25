# Snowpark Container Services - LLM Zoo
This repository contains code to run various Large Language Models (LLMs) in Snowpark Container Services.  

## Requirements
* Snowflake Account with Snowpark Container Services
* Docker installed

## Compute Requirements
Snowflake currently offers three different types of GPU pools:
* GPU_NV_S (1x NVIDIA A10G)
* GPU_NV_M (4x NVIDIA A10G)
* GPU_NV_L (8x NVIDIA A100)

Each model has different GPU requirements which I list in the subfolders.  
If your model only requires a small GPU pool, you can skip the steps of creating a medium and large pool.

## General Setup Instructions
### 1. Setup the Snowflake environment
```sql
USE ROLE ACCOUNTADMIN;

CREATE DATABASE IF NOT EXISTS LLM_DB;
-- Stage where we'll store service specifications
CREATE STAGE IF NOT EXISTS LLM_DB.PUBLIC.CONTAINER_FILES
    ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE') 
    DIRECTORY = (ENABLE = TRUE);
-- Stage where we'll store Llama 3 model files
CREATE STAGE IF NOT EXISTS LLM_DB.PUBLIC.LLM_MODELS 
    ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE') 
    DIRECTORY = (ENABLE = TRUE);

-- Create Compute Pool in which smaller LLM services will be executed
CREATE COMPUTE POOL LLM_GPU_POOL_SMALL
  MIN_NODES = 1
  MAX_NODES = 10
  INSTANCE_FAMILY = GPU_NV_S;

-- Create Compute Pool in which medium LLM services will be executed
CREATE COMPUTE POOL LLM_GPU_POOL_MEDIUM
  MIN_NODES = 1
  MAX_NODES = 5
  INSTANCE_FAMILY = GPU_NV_M;

-- Create Compute Pool in which large LLM services will be executed
CREATE COMPUTE POOL LLM_GPU_POOL_LARGE
  MIN_NODES = 1
  MAX_NODES = 1
  INSTANCE_FAMILY = GPU_NV_L;

-- Create Image Repository
CREATE IMAGE REPOSITORY LLM_DB.PUBLIC.IMAGE_REPOSITORY;

-- Create External Access Integration (to download LLama 3 models)
CREATE OR REPLACE NETWORK RULE LLM_DB.PUBLIC.LLM_NETWORK_RULE
    MODE = EGRESS
    TYPE = HOST_PORT
    VALUE_LIST = ('0.0.0.0:443','0.0.0.0:80');

CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION LLM_ACCESS_INTEGRATION
    ALLOWED_NETWORK_RULES = (LLM_DB.PUBLIC.LLM_NETWORK_RULE)
    ENABLED = true;

-- Create a secret for downloading Hugging Face Models
CREATE SECRET LLM_DB.PUBLIC.HUGGINGFACE_TOKEN
    TYPE = GENERIC_STRING
    SECRET_STRING = 'hf_<your-token>'
    COMMENT = 'Hugging Face User Access Token';

-- Create a custom role for LLM services
-- Grants for custom role to create and run LLM services
CREATE OR REPLACE ROLE LLM_ROLE;
GRANT USAGE ON DATABASE LLM_DB TO ROLE LLM_ROLE;
GRANT USAGE ON SCHEMA LLM_DB.PUBLIC TO ROLE LLM_ROLE;
GRANT READ ON IMAGE REPOSITORY LLM_DB.PUBLIC.IMAGE_REPOSITORY TO ROLE LLM_ROLE;
GRANT CREATE FUNCTION ON SCHEMA LLM_DB.PUBLIC TO ROLE LLM_ROLE;
GRANT CREATE SERVICE ON SCHEMA LLM_DB.PUBLIC TO ROLE LLM_ROLE;
GRANT READ ON STAGE LLM_DB.PUBLIC.CONTAINER_FILES TO ROLE LLM_ROLE;
GRANT READ, WRITE ON STAGE LLM_DB.PUBLIC.LLM_MODELS TO ROLE LLM_ROLE;
GRANT USAGE, OPERATE, MONITOR ON COMPUTE POOL LLM_GPU_POOL_SMALL TO ROLE LLM_ROLE;
GRANT USAGE, OPERATE, MONITOR ON COMPUTE POOL LLM_GPU_POOL_MEDIUM TO ROLE LLM_ROLE;
GRANT USAGE ON NETWORK RULE LLM_DB.PUBLIC.LLM_NETWORK_RULE TO ROLE LLM_ROLE;
GRANT USAGE ON INTEGRATION LLM_ACCESS_INTEGRATION TO ROLE LLM_ROLE;
GRANT USAGE ON SECRET LLM_DB.PUBLIC.HUGGINGFACE_TOKEN TO ROLE LLM_ROLE;
GRANT READ ON SECRET LLM_DB.PUBLIC.HUGGINGFACE_TOKEN TO ROLE LLM_ROLE;
GRANT ROLE LLM_ROLE TO USER ADMIN; --add your username here
```
### 2. Clone this Repository
```bash
git clone https://github.com/michaelgorkow/scs_llm_zoo.git
```

### 3. Deploy the Models
Please follow the steps described in each model's subfolder.