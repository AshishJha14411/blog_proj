"""Celery task modules.

Each task lives in a topic-scoped file (email.py, moderation.py, …) and is
imported via app/worker.py's `include=[...]`. Do not add cross-module imports
here — a task should be constructible from its arguments alone so Celery can
serialize + retry it without carrying request state.
"""
