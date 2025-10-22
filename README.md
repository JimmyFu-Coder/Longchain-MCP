# Longchain-MCP

🧠 Milestone 1: Streaming Response (Typewriter Experience)
🎯 Goal

Enable streaming responses from the backend to the frontend so that users can see the AI's reply as it is being generated, similar to the typing effect in ChatGPT
.

🧭 Feature Breakdown
Feature	Description	Status
1. LLM streaming function	Use astream() to stream tokens from the LLM	✅
2. FastAPI streaming route	Return StreamingResponse instead of one-shot text	✅
3. CORS support	Allow frontend (React) to access API from another origin	✅
4. Fetch streaming in React	Consume token stream using ReadableStream	✅
5. Live output rendering	Append streamed text in real time	✅
6. Loading state	Disable button and show “Streaming…” while in progress	✅
7. Error handling	Show error message on failure	✅
8. Auto scroll	Keep output box scrolled to the bottom while streaming	✅
9. Documentation	This README 😎	✅
🧰 Tech Stack

Backend: FastAPI + LangChain (Azure OpenAI)

Frontend: React + Fetch API streaming

LLM: GPT-4.1-nano via Azure OpenAI Service

Styling: Custom CSS (Dark Mode UI)
