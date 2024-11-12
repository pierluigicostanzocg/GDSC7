from typing import Any, Dict, Optional, Sequence, Type, Union
from sqlalchemy.engine import Result

from langchain_community.tools.sql_database.tool import BaseSQLDatabaseTool, InfoSQLDatabaseTool
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from langchain_community.utilities.sql_database import SQLDatabase

from langchain_core.pydantic_v1 import BaseModel, Field

import os

#Database
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_USER = os.environ["DB_USER"]
DB_ENDPOINT = os.environ["DB_ENDPOINT"]
DB_PORT = os.environ["DB_PORT"]
DB_NAME ='postgres'

DB_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_ENDPOINT}:{DB_PORT}/{DB_NAME}'
db_200 = SQLDatabase.from_uri(DB_URL, sample_rows_in_table_info=200)
db_5 = SQLDatabase.from_uri(DB_URL, sample_rows_in_table_info=5)

class InfoSQLDatabaseToolV2(InfoSQLDatabaseTool):
    def _run(
        self,
        table_names: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Get the schema for tables in a comma-separated list."""
        pirls_tables = [
            'benchmarks', 'countries', 'studentscoreentries',
            'studentquestionnaireentries', 'schoolquestionnaireentries', 'homequestionnaireentries', 'curriculumquestionnaireentries',

            'students', 'studentquestionnaireanswers', 'studentscoreresults', 'studentteachers',
            'curricula', 'curriculumquestionnaireanswers', 
            'homes', 'homequestionnaireanswers', 
            'schools', 'schoolquestionnaireanswers',
            'teachers', 'teacherquestionnaireanswers', 'teacherquestionnaireentries']

        pirls_tables_schema = []
        for pt in pirls_tables:
            db_use = self.db
            if pt in ['benchmarks', 'countries', 'studentscoreentries', 'studentquestionnaireentries', 'schoolquestionnaireentries', 'homequestionnaireentries', 'curriculumquestionnaireentries']:
                db_use = db_200
            else: db_use = db_5
            pirls_tables_schema.append(db_use.get_table_info_no_throw([pt]))
        return "\n\n".join(pirls_tables_schema)

class _QuerySQLDataBaseToolInputV2(BaseModel):
    query: str = Field(..., description="A detailed and correct SQL query. Must be simple to visualize in one of 2D chart, bar, line, scatter, with max 10 values.")
    chart: str = Field(..., description="2D chart. Can ONLY be: bar, line, scatter, None")
    x_axis_chart: str = Field(..., description="name of the column of the chart x axis. If chart is None, x axis is also None.")
    y_axis_chart: str = Field(..., description="name of the column of the chart y axis. If chart is None, y axis is also None.")
    chart_explanation: str = Field(..., description="Explaination of what insight from this chart relevant to the user ask. If chart is None, chart_explanation is also None.")

class QuerySQLDataBaseToolV2(BaseSQLDatabaseTool, BaseTool):
    """Tool for querying a SQL database."""

    name: str = "sql_db_query"
    description: str = """
    Execute a SQL query against the database and get back the result and which chart can be used to visualize the data.
    If the query is not correct, an error message will be returned and the chart is None.
    If an error is returned, rewrite the query, check the query, and try again.
    """
    args_schema: Type[BaseModel] = _QuerySQLDataBaseToolInputV2

    def _run(
        self,
        query: str,
        chart: str,
        x_axis_chart: str,
        y_axis_chart: str,
        chart_explanation: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Union[str, Sequence[Dict[str, Any]], Result]:
        """Execute the query, return the results (query, data, chart, x_axis_chart, y_axis_chart, chart_description, chart_explanation) or an error message."""
        return query, self.db.run_no_throw(query), chart, x_axis_chart, y_axis_chart, chart_explanation