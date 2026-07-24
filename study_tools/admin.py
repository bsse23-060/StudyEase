from django.contrib import admin
from .models import Citation, Conversation, Document, DocumentChunk, Flashcard, FlashcardDeck, Message, ProviderUsage, Routine, ScheduleBlock
admin.site.register((Document, DocumentChunk, Conversation, Message, Citation, ProviderUsage, FlashcardDeck, Flashcard, Routine, ScheduleBlock))
