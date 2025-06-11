## MentaLLM

MentaLLM is a modular **LLM-powered mental health assistant prototype** built with Flask and LangChain.
Users can register, log in, and engage in a personalized conversation with an AI chatbot.
The project aims to demonstrate how LLM-based chatbot systems can be developed for both developers and researchers.

## Purpose of the Project

This project lays the foundation for an assistant system capable of one-on-one interaction with users by leveraging Large Language Models (LLMs).
MentaLLM goes beyond simple LLM responses by offering personalization, memory management, and knowledge-based answer generation.

Kapsamında şunlar yer alır:
- Contextual conversation experience with the chatbot (LangChain-based)
- Context-aware response generation with memory (via LangChain’s ConversationBufferMemory)
- Knowledge-based answering using Chroma vector database
- Custom prompt formatting using PromptTemplate
- Secure management of API keys using dotenv
- Modular project structure (separated logic for chat, login, database, user profile)
- Clean and user-friendly web interface (Jinja2 templating)
- Architecture designed for future extensibility (compatible with REST API, JWT, Docker, etc.)

## Technologies Used

| Teknoloji        | Açıklama |
|------------------|----------|
| `Python 3.10+`   | Core programming language |
| `Flask`          | Web server, routing, and HTML templating engine |
| `SQLite`         | Lightweight, embedded database system |
| `LangChain`      | LLM interaction and memory management |
| `Chroma`         | Local vector database (retriever for context-aware responses) |
| `OpenAI API`     | Integration with GPT-4o / GPT-4 / GPT-3.5 models |
| `python-dotenv`  | Secure environment variable management|
| `HTML/CSS`       | User interface design (via Jinja2 templates) |
