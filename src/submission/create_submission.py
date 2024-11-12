import dotenv

from src.static.ChatBedrockWrapper import ChatBedrockWrapper
from src.static.submission import Submission
from src.submission.crews.agentFOX_tools import AgentFOXPIRLSCrew

dotenv.load_dotenv()


# This function is used to run evaluation of your model.
# You MUST NOT change the signature of this function! The name of the function, name of the arguments,
# number of the arguments and the returned type mustn't be changed.
# You can modify only the body of this function so that it returned your implementation of the Submission class.
def create_submission(call_id: str) -> Submission:
    MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    chat_model = ChatBedrockWrapper(model_id=MODEL_ID, model_kwargs={'temperature': 0.2}, call_id=call_id)
    crew = AgentFOXPIRLSCrew(chat_model)
    return crew
