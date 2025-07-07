# api/ai/qa_schemas.py
from pydantic import BaseModel


class QAQuery(BaseModel):
    question: str


class QAResponse(BaseModel):
    answer: str
