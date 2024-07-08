# Import python packages
import streamlit as st
import pandas as pd
from io import BytesIO
from PIL import Image
from snowflake.snowpark.context import get_active_session

with st.sidebar:
    # Write directly to the app
    st.title("Multimodal Model in Snowflake! 🤖📄🖼️")
    st.markdown("Model: [THUDM/glm-4v-9b model.](https://huggingface.co/THUDM/glm-4v-9b)")
    prompt = st.text_area('Prompt: ', value='Describe this image.')
    max_length = st.slider('max_length:', value=2500, min_value=10, max_value=5000)
    top_k = st.slider('top_k:', value=1, min_value=1, max_value=100)
    top_p = st.slider('top_p:', value=0.8, min_value=0.0, max_value=1.0)
    temperature = st.slider('temperature:', value=0.8, min_value=0.0, max_value=1.0)

# Get the current credentials
session = get_active_session()

tab1, tab2, tab3 = st.tabs(['Standard Chatting', 'Query Image data in Snowflake','Query Image data from URLs'])

# index, input_prompt, generation_args
with tab1:
    if st.button('Ask!'):
        generation_args = {'max_length':max_length,'top_k':top_k,'top_p':top_p,'temperature':temperature}
        res = session.sql(f"""
            SELECT LLM_DB.PUBLIC.GLM_V4_9B_COMPLETE(
                '{prompt}',
                {generation_args}) AS RESPONSE""").collect()[0]['RESPONSE']
        st.info(res)

with tab2:
    stages = pd.DataFrame(session.sql("SHOW STAGES like 'IMAGE_FILES'").collect())
    stages['FULL_PATH'] = stages['database_name'] + '.' + stages['schema_name'] + '.' + stages['name']
    stages = stages.sort_values(by=['database_name', 'schema_name', 'name'])
    stage_selection = st.selectbox('Select Stage:', stages['FULL_PATH'])
    files = pd.DataFrame(session.sql(f"SELECT RELATIVE_PATH FROM DIRECTORY(@{stage_selection})").collect())
    files = files.sort_values(by=['RELATIVE_PATH'])
    file_selection = st.selectbox('Select File:', files['RELATIVE_PATH'])
    image = session.file.get_stream(f"@{stage_selection}/{file_selection}")
    image = Image.open(BytesIO(image.read()))
    st.image(image)
    #prompt = st.text_area('Prompt: ')
    if st.button('Query my image in Snowflake!'):
        generation_args = {'max_length':max_length,'top_k':top_k,'top_p':top_p,'temperature':temperature}
        res = session.sql(f"""
            SELECT LLM_DB.PUBLIC.GLM_V4_9B_COMPLETE_IMAGE(
                '{prompt}',
                {generation_args},
                GET_PRESIGNED_URL('@{stage_selection}', '{file_selection}')) AS RESPONSE""").collect()[0]['RESPONSE']
        st.info(res)

with tab3:
    url = st.text_input('URL:', value='https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTGtsjtT26xLbvGO_eRAcJJ2drgv6wC9S7REQ&s')
    #prompt = st.text_area('Prompt:')
    if st.button('Query my image url!'):
        generation_args = {'max_length':max_length,'top_k':top_k,'top_p':top_p,'temperature':temperature}
        res = session.sql(f"""
            SELECT LLM_DB.PUBLIC.GLM_V4_9B_COMPLETE_IMAGE(
            '{prompt}',
            {generation_args},
            '{url}') AS RESPONSE""").collect()[0]['RESPONSE']
        st.info(res)