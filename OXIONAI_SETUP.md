# OxionAI integration

## GitHub Actions secrets
Add two repository Actions secrets:
- OXIONAI_RESEARCH_API_KEY: API key for the research account.
- OXIONAI_WRITER_API_KEY: API key for the writing account.

Keys are never stored in source code. Research and writing credentials are kept separate;
there is no automatic cross-account key rotation.

## Models
- Research: gemini-3.7-flash
- Writing: deepseek-v4-flash-0731
- API base: https://www.oxionai.com/v1

The model IDs and OpenAI-compatible chat completions interface are documented by OxionAI.
The research model is asked to use native web search where available and must return
source URLs. The pipeline cannot independently prove the model actually searched; inspect
output/ai_content_audit.json and verify sources before treating claims as fact.

## Safeguards
The current reviewed local story is selected first and remains the fallback. AI output is
accepted only when research returns at least two HTTPS source URLs and two facts, and the
writer returns a 65-120 word narration, title and at least three image queries. Any missing
secret, API failure, malformed JSON, or validation failure retains the local story and
does not stop video generation or publishing.

Token usage from both API responses is logged and stored in the audit JSON artifact.
