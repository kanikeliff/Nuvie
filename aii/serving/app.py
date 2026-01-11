"""
Deprecated standalone AI FastAPI app.

This module previously exposed a separate FastAPI app and routes under
`/ai/*`, which caused duplicate endpoints when the main backend imported
AI code. The original implementation has been moved to
`aii/serving/app_deprecated.py` as a reference. Do not import this module
from the main backend application.

If you need to run the standalone AI service, copy the deprecated file
and run it as a separate process, ensuring it doesn't get imported by the
backend app at import-time.
"""
