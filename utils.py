from deepeval.models.base_model import DeepEvalBaseLLM
from config import settings 
from langchain_openai import ChatOpenAI

class EvalModel(DeepEvalBaseLLM):
    def __init__(self):
        self.model_name = settings.openai_eval_model
        self.model = ChatOpenAI(
            model=self.model_name,
            temperature=0,
            openai_api_base=settings.openai_api_base,
            openai_api_key=settings.openai_api_key
        )

    def load_model(self) -> ChatOpenAI:
        return self.model

    def generate(self, prompt: str) -> str:
        model = self.load_model()
        res = model.invoke(prompt)
        return res.content
    
    async def a_generate(self, prompt: str) -> str:
        model = self.load_model()
        res = await model.ainvoke(prompt)
        return res.content
    
    def get_model_name(self) -> str:
        return self.model_name