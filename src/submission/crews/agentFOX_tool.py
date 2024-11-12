from src.static.submission import Submission
from src.static.ChatBedrockWrapper import ChatBedrockWrapper
from src.submission.crews.util import InfoSQLDatabaseToolV2, QuerySQLDataBaseToolV2

from typing import List
from langchain_core.tools import BaseTool

from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities.sql_database import SQLDatabase
from langgraph.prebuilt import create_react_agent
from langchain import hub

import json
import os
import io
import requests
import boto3.session
import boto3

# Database
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_USER = os.environ["DB_USER"]
DB_ENDPOINT = os.environ["DB_ENDPOINT"]
DB_PORT = os.environ["DB_PORT"]
DB_NAME ='postgres'

DB_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_ENDPOINT}:{DB_PORT}/{DB_NAME}'
DB = SQLDatabase.from_uri(DB_URL, sample_rows_in_table_info=500)

# Pull prompt from LangChain
PROMPT_TEMPLATE = hub.pull("langchain-ai/sql-agent-system-prompt")
SYSTEM_MESSAGE = PROMPT_TEMPLATE.format(dialect="SQLite", top_k=1000)


# FUNCTION to customize the SQL Toolkit
def get_toolkit_tools(chat_model: ChatBedrockWrapper) -> List[BaseTool]:
    """
    Replace the default LangChain Info and Query Database Tools with the custom ones.
    Return the customized SQL Toolkit
    """
    toolkit = SQLDatabaseToolkit(db=DB, llm=chat_model)
    toolkit_tools = toolkit.get_tools()
    toolkit_tools[0] = QuerySQLDataBaseToolV2(db=DB, description=toolkit_tools[0].description)
    toolkit_tools[1] = InfoSQLDatabaseToolV2(db=DB, description=toolkit_tools[1].description)
    return toolkit_tools


# FUNCTION to clean and extract the viz section
def get_viz_section(m_events: list) -> str:
    """
    - Get the output of the LangChain runnable
    - Extract the messages with `sql_db_query` tool
    - Filter the last 3 `viz` messages and clean-up
    - use quickchart to generate a chart with the parameter from the tool output message
    - save the chart in s3 bucket
    
    Return the markdown of the viz section of the output
    """

    charts_llm = []
    for e in m_events['messages']:
        if e.name == 'sql_db_query':
            try:
                test_try = ( eval(e.content), len(eval(e.content)) )
                if len(eval(eval(e.content)[1])) > 0:
                    charts_llm.append([eval(n) if i == 1 else n for i,n in enumerate(eval(e.content))])
            except:
                pass
    
    charts_llm_viz = []
    for c in charts_llm[-min(3, len(charts_llm)):]:
        try:
            if c[2] in ['bar', 'line', 'scatter']:
                params = {
                    'chart': json.dumps({
                        "type": c[2],
                        "data": {
                            "labels": list(map(lambda x: x[0], c[1]))[:15],
                            "datasets": [{
                                "label": "",
                                "data": list(map(lambda x: x[1], c[1]))[:15],
                                "backgroundColor": '#1CABE2',
                                "borderColor": '#1CABE2',
                            }]
                        },
                        'options': {
                            'legend': {'display': False,},
                            'title': {'display': False},
                        }
                    }),
                    'width': 600,
                    'height': 300,
                    'backgroundColor': 'white',
                    "devicePixelRatio": 1,
                }
                quickchart_url = 'https://quickchart.io/chart/create'
                post_data = params
                response = requests.post(
                    quickchart_url,
                    json=post_data,
                )
                if (response.status_code != 200):
                    print('Error:', response.text)
                else:
                    chart_response = json.loads(response.text)
                    print(chart_response)
                    chart_response_url = chart_response["url"]
                    filename = chart_response_url.split("/")[-1]
                    img_data = requests.get(chart_response_url).content
                    from io import BytesIO
                    img_data = BytesIO(img_data)
                    
                    # Upload the image to S3
                    session = boto3.Session()
                    s3 = session.client('s3')
                    bucket_name = 'gdsc-bucket-<>'
                    try:
                        s3.upload_fileobj(img_data, bucket_name, filename)
                        # Build and return the S3 URL
                        s3_url = f'https://{bucket_name}.s3.amazonaws.com/{filename}'
                        print(s3_url)
                    
                        charts_llm_viz.append(f"""
- {c[-1]}

    ![]({s3_url})

""")
                    except Exception as e:
                        print(f"An error occurred: {str(e)}")
        except:
            pass
    if charts_llm_viz:
        charts_llm_viz = '\n\n\n'.join(charts_llm_viz)
        charts_llm_viz = f"""
\n\n

Here insights from from relevant **visuals**:

{charts_llm_viz}

\n\n

"""
    else: charts_llm_viz = """"""

    return charts_llm_viz


# MAIN Class section
class AgentFOXPIRLSCrew(Submission):

    def __init__(self, llm: ChatBedrockWrapper):
        self.llm = llm
        self.toolkit_tools = get_toolkit_tools(llm)
        self.executor = create_react_agent(llm, self.toolkit_tools, state_modifier=SYSTEM_MESSAGE)

    def run(self, prompt: str) -> str:
        agent_executor = self.executor
        
        # Query agent
        example_query = f"""{prompt}"""
        
        # Get event messages
        events = agent_executor.invoke(
            {"messages": [("user", f"""
If the input is not relevant to the PIRLS data, explain politely that you can help only with PIRLS data.

Return an insightful but straight short simple answer.

The following are important instructions about the database:
- student_id, school_id, home_id, teacher_id ONLY for join and return ONLY as count.
- ALWAYS clarify which benchmarks.name, benchmarks.score threshold, studentscoreentries.name, countries.benchmark.
- DO NOT return country_id, benchmark_id, code, BUT return their respective name, type, question, and answer.
- Prefer column type for understanding the questions in the database, use FILTER BY.
- Prefer aggregate GROUP BY benchmarks.name.
- Prefer aggregate GROUP BY studentscoreentries.name.
- Prefer separate query for each countries.benchmark column and indicate the countries.benchmark in your answer.
- Prefer separate query for each question column, then aggregate GROUP BY answer column.
- Prefer percentage aggregated data
- DO NOT return raw data.
- MAX five simple SQL queries which return ALWAYS two columns, relevant to the user ask.

The format MUST be a well-structured markdown, few comments, careful on using correct line breaks and DO NOT use images.

DO NOT apologize for mistakes or errors, just give an answer without much verbosity.
Keep it simple with max three short bullet points.
Tone to be data-driven, professional.

Make sure the user ask is clear and the data is relevant.

Question: {example_query}
            """)]},
            {"recursion_limit": 100},
            stream_mode="values",
        )
        
        # Get viz section
        charts_llm_viz = get_viz_section(events)
        
        # Prepare output
        output_answer = f"""

{events['messages'][-1].content}

***

{charts_llm_viz}

"""
        return str(output_answer)