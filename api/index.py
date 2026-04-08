"""Vercel Python entrypoint for DAY VIBE AI."""

from trendradar.assistant.web import AssistantHTTPRequestHandler


class handler(AssistantHTTPRequestHandler):
    """Top-level handler required by Vercel runtime."""

