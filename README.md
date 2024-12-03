

# README

## Intelligent Chatbot Agent

### Setup Instructions

1. **Clone the Repository**

   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Create a Virtual Environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Application**

   ```bash
   python main.py
   ```

### Architecture Overview

The project structure is as follows:

```
├── .env
├── assignment_task.txt
├── index.html
├── main.py
├── README.md
├── requirements.txt
└── src
    ├── retrieval_graph
    │   ├── __init__.py
    │   ├── configuration.py
    │   ├── graph.py
    │   ├── prompts.py
    │   └── state.py
    └── shared
        ├── __init__.py
        ├── configuration.py
        ├── index
        │   ├── index.faiss
        │   └── index.pkl
        ├── index_test.py
        ├── retrieval.py
        ├── state.py
        └── utils.py
```

- **`main.py`**: Entry point of the application.
- **

src

**: Contains all source code.
  - **`retrieval_graph/`**: Manages the conversation flow and RAG implementation.
    - **`graph.py`**: Core logic for handling conversation states and actions.
    - **`prompts.py`**: Contains prompt templates used in the chatbot.
    - **

state.py

**: Manages the agent's state throughout the conversation.
    - **`configuration.py`**: Specific configurations for the retrieval graph.
  - **`shared/`**: Shared utilities and modules.
    - **`retrieval.py`**: Handles document retrieval using the vector database.
    - **`utils.py`**: Helper functions used across the project.
    - **

state.py

**: Shared state management.
    - **`configuration.py`**: General configurations.
    - **`index/`**: Stores vector index files (`index.faiss`, `index.pkl`).
    - **`index_test.py`**: Tests for the indexing functionality.

### Key Design Decisions

- **Language Choice**: Python was selected for its robust support in AI development and extensive libraries.
- **RAG Implementation**: Employed LangChain or equivalent to implement Retrieval Augmented Generation, providing contextual and accurate responses.
- **Vector Database**: Utilized a vector database (e.g., FAISS) for efficient similarity searches and document retrieval.
- **Real-Time Communication**: Implemented WebSocket connections to enable a seamless, real-time chat interface.
- **Modular Architecture**: Structured the codebase into clear modules to enhance maintainability and scalability.

### Known Limitations

- **Email Functionality**: Currently uses a mock function for sending emails; it doesn't send real emails.
- **Error Handling**: Basic error handling is present, but there's room for more comprehensive exception management.
- **Testing**: Limited tests are included; expanding test coverage would improve reliability.
- **Scalability**: The application may require optimization to handle larger datasets and more users efficiently.

### Future Improvements

- **Integrate Real Email Service**: Connect to an actual email service provider to enable sending real emails to users.
- **Enhance Error Handling**: Implement more robust error handling and logging mechanisms.
- **Increase Test Coverage**: Write additional unit and integration tests to cover more scenarios.
- **Optimize Performance**: Improve indexing and retrieval processes for better scalability.
- **Improve User Interface**: Enhance the 

index.html

 page for a more user-friendly experience.
- **Dockerization and Deployment**: Containerize the application using Docker and set up continuous integration/continuous deployment (CI/CD) pipelines.

---

## Brief Documentation of RAG Implementation

### Overview

The Retrieval Augmented Generation (RAG) implementation allows the chatbot to provide informed and contextually relevant responses by retrieving information from a knowledge base.

### Process Details

1. **Document Ingestion**

   - **Loading the Document**: The provided company PDF document is loaded into the system.
   - **Preprocessing**: The document is split into smaller chunks suitable for processing and embedding.

2. **Creating Vector Embeddings**

   - **Embedding Generation**: Each document chunk is converted into a vector representation using a language model.
   - **Indexing**: The embeddings are stored in a vector database (e.g., FAISS) to enable efficient similarity searches.

3. **Handling User Queries**

   - **Receiving Input**: The chatbot receives queries from the user during the conversation.
   - **Query Embedding**: User queries are converted into vector embeddings using the same language model.

4. **Retrieval Mechanism**

   - **Similarity Search**: The system performs a similarity search between the query embedding and document embeddings.
   - **Relevant Information Extraction**: Retrieves the most relevant document chunks based on the similarity scores.

5. **Generating Responses**

   - **Contextual Response Formation**: The retrieved information is used to generate accurate and contextually appropriate responses.
   - **Leveraging Prompts**: Predefined prompts in `prompts.py` guide the generation of responses to maintain conversation flow.

### Key Components

- **`retrieval_graph/graph.py`**: Manages the conversation logic and integrates the retrieval component to provide responses.
- **`shared/retrieval.py`**: Handles the creation of embeddings, indexing, and retrieval of documents.
- **`shared/index/`**: Stores the vector index files used for similarity searches.
- **`prompts.py`**: Contains templates that ensure the responses are coherent and aligned with the conversation flow.

### Example Function: 

send_company_profile



- This function, defined in 

graph.py

, demonstrates how the system sends the company profile to the user's email (using a mock function) and returns a confirmation message.

   ```python
   async def send_company_profile(state: AgentState, *, config: RunnableConfig) -> dict[str, Any]:
       """Send company profile via email."""
       send_email(state.email, format_docs(state.documents))
       return {
           "messages": [
               AIMessage(content=f"Company profile has been sent to {state.email}. Is there anything else I can help you with?")
           ],
           "email": {"email_sent": True},
           "router": {"type": "overview", "logic": "conversation_complete"}
       }
   ```

### How RAG Enhances the Chatbot

- **Contextual Understanding**: By retrieving relevant information, the chatbot can provide precise answers related to the company's details.
- **Dynamic Responses**: The use of real-time data retrieval allows for up-to-date and accurate information dissemination.
- **Improved User Experience**: Users receive informative responses that are directly relevant to their queries, enhancing satisfaction.

---

This documentation should give you a clear understanding of the project's setup, structure, and the underlying mechanisms that enable the intelligent chatbot to function effectively.
