from django.conf import settings
from django.db import transaction
from study_tools.models import Citation, Conversation, Message
from .generation import generate_grounded_answer
from .retrieval import retrieve_chunks

def answer_question(user, conversation: Conversation, question: str, *, document_ids=None, top_k=None):
    if conversation.owner_id != user.id: raise PermissionError("You do not own this conversation.")
    history_rows = list(conversation.messages.filter(deleted_at__isnull=True).order_by("-created_at")[:settings.RAG_HISTORY_MESSAGE_LIMIT])
    history = [{"role": row.role, "content": row.content[:2000]} for row in reversed(history_rows)]
    retrieval = retrieve_chunks(user, question, course=conversation.course, lesson=conversation.lesson, document_ids=document_ids, top_k=top_k)
    generated = generate_grounded_answer(user, question, retrieval.chunks, history)
    chunk_map = {chunk.id: chunk for chunk in retrieval.chunks}
    with transaction.atomic():
        Message.objects.create(conversation=conversation, role=Message.Role.USER, content=question)
        assistant = Message.objects.create(conversation=conversation, role=Message.Role.ASSISTANT, content=generated.answer, metadata={"has_sufficient_context": generated.has_sufficient_context})
        Citation.objects.bulk_create([Citation(message=assistant, chunk_id=item.chunk_id, quote=item.supporting_text, score=chunk_map[item.chunk_id].score) for item in generated.citations])
    return assistant
