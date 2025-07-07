# api/routers/qa.py
from fastapi import APIRouter, Depends, HTTPException
from ..ai.qa_service import rag_chain
from ..ai.qa_schemas import QAQuery, QAResponse
from ..schemas import User
from .auth import get_current_user

router = APIRouter(
    prefix="/qa",
    tags=["Q&A"],
)


@router.post("/", response_model=QAResponse)
async def question_and_answer(
    request: QAQuery,
    current_user: User = Depends(get_current_user),  # Secure the endpoint
):
    """
    Accepts a user question and returns an answer using the RAG chain.
    """
    try:
        result = await rag_chain.ainvoke({"question": request.question})
        return QAResponse(answer=result.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
