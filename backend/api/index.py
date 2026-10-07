"""Vercel entrypoint for the FastAPI application.

Vercel loads this file as a serverless function. Two details matter:

* ``sys.path`` — the ``app`` package lives one directory above this file. Vercel
  normally puts the project root on the path, but adding it explicitly means the
  function also works if the layout changes (for example when the app is served
  from a subdirectory), and it makes the import error self-explanatory if it
  ever fails.

* No local state survives. Every invocation gets a fresh, read-only filesystem
  apart from ``/tmp``, so the app redirects its storage there (see
  ``Settings.set_storage_dir``). Projects uploaded in one request will not be
  visible from another, which is fine for a demo and not for real use — the
  constraints are documented in ``docs/deployment-vercel.md``.
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from app.main import app  # noqa: E402  (import after the path fix, deliberately)

__all__ = ["app"]
