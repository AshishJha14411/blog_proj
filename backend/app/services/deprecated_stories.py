# # app/services/stories.py
# from __future__ import annotations
# from datetime import datetime
# from typing import Tuple

# from fastapi import HTTPException, status
# from sqlalchemy.orm import Session

# from app.models.stories import Story, ContentSource, StoryStatus, LengthLabel
# from app.models.story_revision import StoryRevision
# from app.models.user import User
# from app.services.moderation import moderate_content
# from app.llm.adapter import LLMAdapter
# from app.core.config import settings


# _llm = LLMAdapter()



# def generate_story(db: Session, data, current_user: User) -> Story:
#     """
#     Creates a new AI-generated Story (status=generated, is_published per flag/publish_now),
#     saves StoryRevision v1, runs moderation.
#     """
#     full_prompt = _build_story_prompt(
#         user_prompt=data.prompt,
#         genre=data.genre,
#         tone=data.tone,
#         length_label=data.length_label
#     )

#     story_text, msg_id = _generate_story_text(
#         prompt=full_prompt,
#         model=data.model_name or settings.LLM_MODEL,
#         temperature=data.temperature if data.temperature is not None else settings.LLM_TEMPERATURE
#     )

#     # Fallback title from first line if user didn’t provide one
#     title = data.title or _default_title_from(story_text, fallback="Untitled Story")

#     # Moderation (title+content)
#     flagged, cats = moderate_content([title, story_text])

#     # Build Story
#     post = Story(
#         user_id=current_user.id,
#         title=title,
#         header=data.summary,
#         content=story_text,
#         cover_image_url=str(data.cover_image_url) if data.cover_image_url else None,

#         # Visibility: default to not published; if publish_now and not flagged → publish
#         is_published=(data.publish_now and not flagged),

#         is_flagged=flagged,
#         flag_source="ai" if flagged else "none",
#         created_at=datetime.utcnow(),
#         updated_at=datetime.utcnow(),

#         # Story metadata
#         source=ContentSource.ai,
#         genre=data.genre,
#         tone=data.tone,
#         length_label=LengthLabel(data.length_label) if data.length_label else None,
#         summary=data.summary,
#         words_count=_count_words(story_text),

#         # Workflow + provenance
#         status=(StoryStatus.published if (data.publish_now and not flagged) else StoryStatus.generated),
#         prompt=data.prompt,
#         model_name=(data.model_name or settings.LLM_MODEL),
#         temperature=(data.temperature if data.temperature is not None else settings.LLM_TEMPERATURE),
#         provider_message_id=msg_id,

#         # Versioning
#         parent_id=None,
#         version=1,
#         last_feedback=None
#     )
#     if post.version>1:
#         db.add(StoryRevision(
#         post_id=post.id,
#         version=1,
#         content=story_text,
#         prompt=data.prompt,
#         feedback=None,
#         model_name=post.model_name,
#         provider_message_id=msg_id,
#         user_id=current_user.id, 
#     ))
#     db.add(post)
#     db.flush()  # need post.id

#     # First revision record
    

#     db.commit()
#     db.refresh(post)
#     return post


# def regenerate_with_feedback(db: Session, post_id: int, feedback: str, current_user: User) -> Story:
#     """
#     Uses previous post.prompt + user feedback to regenerate story.
#     Increments version, writes a new StoryRevision, resets publish state (generated).
#     """
#     post = db.query(Story).filter(Story.id == post_id, Story.deleted_at == None).first()
#     if not post:
#         raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")

#     _ensure_authorization(post, current_user)

#     regen_prompt = _build_regen_prompt(base_prompt=post.prompt or "", feedback=feedback)

#     new_text, msg_id = _generate_story_text(
#         prompt=regen_prompt,
#         model=post.model_name or settings.LLM_MODEL,
#         temperature=post.temperature if post.temperature is not None else settings.LLM_TEMPERATURE
#     )

#     flagged, cats = moderate_content([post.title, new_text])

#     # bump version & update post
#     post.version = (post.version or 1) + 1
#     post.content = new_text
#     post.words_count = _count_words(new_text)
#     post.updated_at = datetime.utcnow()
#     post.last_feedback = feedback
#     post.is_flagged = flagged
#     post.is_published = False  # require explicit republish
#     post.status = StoryStatus.generated

#     db.add(StoryRevision(
#         post_id=post.id,
#         version=post.version,
#         content=new_text,
#         prompt=regen_prompt,
#         feedback=feedback,
#         model_name=post.model_name,
#         provider_message_id=msg_id,
#         user_id=current_user.id
#     ))

#     db.commit()
#     db.refresh(post)
#     return post


# def publish_story(db: Session, post_id: int, current_user: User) -> Story:
#     post = db.query(Story).filter(Story.id == post_id, Story.deleted_at == None).first()
#     if not post:
#         raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")
#     _ensure_authorization(post, current_user)

#     if post.is_flagged:
#         raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Story flagged; resolve before publishing.")

#     post.is_published = True
#     post.status = StoryStatus.published
#     post.updated_at = datetime.utcnow()
#     db.commit()
#     db.refresh(post)
#     return post


# def unpublish_story(db: Session, post_id: int, current_user: User) -> Story:
#     post = db.query(Story).filter(Story.id == post_id, Story.deleted_at == None).first()
#     if not post:
#         raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Story not found")
#     _ensure_authorization(post, current_user)

#     post.is_published = False
#     post.status = StoryStatus.generated
#     post.updated_at = datetime.utcnow()
#     db.commit()
#     db.refresh(post)
#     return post


# #  HELPERS FUNCTION

# def _generate_story_text(*, prompt: str, model: str, temperature: float) -> Tuple[str, str]:
#     text, msg_id = _llm.generate(
#         prompt,
#         model=model,
#         temperature=temperature,
#         max_tokens=settings.LLM_MAX_TOKENS,
#         timeout=settings.LLM_TIMEOUT,
#     )
#     if not text.strip():
#         raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="LLM returned empty text")
#     return text, msg_id


# def _build_story_prompt(user_prompt: str, genre: str|None, tone: str|None, length_label: str|None) -> str:
#     return f"""
# You are a skilled fiction writer. Write a complete short story based on the instructions below.

# Output STRICTLY valid, minimal HTML. Use:
# - <h1> for the title (if you invent one)
# - <p> for paragraphs (no extra CSS)
# - <em> for whispers or inner thoughts
# - Use explicit line breaks with <br/> only inside poems/notes
# - When a sound effect occurs, insert a bracketed cue like [SFX: door slam]
# - Do NOT include <html>, <head>, or <body> tags. Only the story fragment HTML.

# Constraints:
# - Genre: {genre or "any"}
# - Tone: {tone or "any"}
# - Length: {length_label or "short"} (aim within that range)
# - Keep it readable on web; short paragraphs.

# Instructions/theme:
# {user_prompt}
# """.strip()

# def _build_regen_prompt(base_prompt: str, feedback: str) -> str:
#     return (
#         "Revise the following short story per the reader feedback.\n\n"
#         "Guidelines:\n"
#         "- Preserve the core idea and characters.\n"
#         "- Improve pacing and clarity.\n"
#         "- Keep the same length range.\n"
#         "- Avoid explicit sexual content, hate speech, and graphic violence.\n\n"
#         f"Original instructions/context:\n{base_prompt}\n\n"
#         f"Reader feedback to address:\n{feedback}\n\n"
#         "Return only the revised story text, no commentary."
#     )


# def _default_title_from(story_text: str, fallback: str = "Untitled Story") -> str:
#     line = (story_text or "").strip().splitlines()[0].strip()
#     if 5 <= len(line) <= 80:
#         return line
#     return fallback


# def _count_words(text: str) -> int:
#     return len((text or "").split())


# def _ensure_authorization(post: Story, user: User):
#     if (post.user_id != user.id) and (user.role.name not in ("moderator", "superadmin")):
#         raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not authorized for this post")
