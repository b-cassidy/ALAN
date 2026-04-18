import os
import ollama
from langchain_community.document_loaders import (
    PyMuPDFLoader,
    DirectoryLoader,
    Docx2txtLoader,
    TextLoader,
    UnstructuredExcelLoader
)
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate


class AlanEngine:
    """
    ALAN (Automated Local Analysis Network) Engine
    Handles document ingestion, vector storage, and RAG-based querying.
    """

    def __init__(self, model_name="llama3.1:8b", embed_model="mxbai-embed-large"):
        self.model_name = model_name
        self.embeddings = OllamaEmbeddings(model=embed_model)
        self.vector_db = None
        self.persist_directory = "./vector_store"
        self.data_path = "./data"
        self.valid_extensions = (
            # List of file types to be ingested
            '.pdf', '.docx', '.doc', '.txt', '.xlsx', '.xls')

        # Create list of files to be ingested based on the contents of the data folder
        if os.path.exists(self.data_path):
            self.filenames = [f for f in os.listdir(self.data_path)
                              if f.lower().endswith(self.valid_extensions)]
        else:
            self.filenames = []

    def ingest_data(self, directory_path="./data", progress_callback=None):
        """
        Scans the directory for supported files, chunks text, and builds the ChromaDB.
        """
        if not os.path.exists(directory_path):
            return f"Error: Directory {directory_path} does not exist."

        # Based on filetype set loader to be used
        loader_mapping = {
            ".pdf": PyMuPDFLoader,
            ".docx": Docx2txtLoader,
            ".doc": Docx2txtLoader,
            ".txt": TextLoader,
            ".xlsx": UnstructuredExcelLoader,
            ".xls": UnstructuredExcelLoader,
        }

        # Sync filename list
        self.filenames = [f for f in os.listdir(directory_path)
                          if f.lower().endswith(self.valid_extensions)]

        print(
            f"--- ALAN Ingestion Started: {len(self.filenames)} files detected ---")

        all_docs = []
        for ext, loader_class in loader_mapping.items():
            try:
                # DirectoryLoader filters by glob pattern for each extension
                loader = DirectoryLoader(
                    directory_path,
                    glob=f"**/*{ext}",
                    loader_cls=loader_class,
                    silent_errors=True  # Prevents one bad file from stopping the whole run
                )
                loaded_docs = loader.load()
                if loaded_docs:
                    print(f"Loaded {len(loaded_docs)} pages from {ext} files.")
                    all_docs.extend(loaded_docs)
            except Exception as e:
                print(f"Warning: Could not load {ext} files. {e}")

        if not all_docs:
            return "No valid text found. Please check your /data folder contents."

        # Splitting text into manageable chunks for the LLM context window
        text_splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", " ", ""],
            chunk_size=500,
            chunk_overlap=50
        )
        chunks = text_splitter.split_documents(all_docs)

        if chunks:
            print(f"Processing {len(chunks)} text chunks...")
            # Initialize/Reset the Vector DB with the first chunk
            self.vector_db = Chroma.from_documents(
                documents=[chunks[0]],
                embedding=self.embeddings,
                persist_directory=self.persist_directory
            )

            # Add remaining chunks in batches to prevent Ollama connection timeouts
            batch_size = 100
            for i in range(1, len(chunks), batch_size):
                batch = chunks[i: i + batch_size]
                self.vector_db.add_documents(batch)

                # Calculate percentage progress to feed back to UI
                if progress_callback:
                    percent = min(i + batch_size, len(chunks)) / len(chunks)
                    progress_callback(percent)

                print(
                    f"Indexing Progress: {min(i + batch_size, len(chunks))} / {len(chunks)}")

            return f"Success! ALAN is now trained on {len(self.filenames)} documents."

        return "Failed to process document chunks."

    def ask(self, question):
        """
        Queries the knowledge base and generates an answer using Local LLM.
        """
        # This catches questions about identity and file access BEFORE searching the books.
        q_lower = question.lower()
        identity_keywords = ["who are you",
                             "what is your name", "what are you"]
        library_keywords = ["what do you have access to", "list",
                            "files", "books", "documents", "knowledge base"]

        if any(k in q_lower for k in identity_keywords):
            base_id = "I am ALAN (Automated Local Analysis Network), your private Data Insights Assistant."
            if self.filenames:
                return f"{base_id}\n\nI have been trained on the following local documents:\n" + "\n".join([f"- {f}" for f in self.filenames])
            return f"{base_id} My knowledge base is currently empty."

        if any(k in q_lower for k in library_keywords):
            if self.filenames:
                return "I currently have access to these documents in your local `/data` folder:\n" + "\n".join([f"- {f}" for f in self.filenames])
            return "I don't see any documents in my local knowledge base yet."

        # Load Vector Store if not already in memory
        if self.vector_db is None:
            if os.path.exists(self.persist_directory):
                self.vector_db = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embeddings
                )
            else:
                return "Knowledge base not found. Please run data ingestion first."

        # Top-K Retrieval (k=12 provides a broad context across multiple documents)
        retriever = self.vector_db.as_retriever(search_kwargs={"k": 12})

        template = """
        You are ALAN, a professional Data Insights Assistant. 
        Use the following pieces of retrieved context to answer the question. 
        If the answer isn't in the context, say you don't know—don't make it up.
        Always mention which source file you are using in your answer.

        Context:
        {context}

        Question: {question}

        Answer:
        """

        def format_context(docs):
            return "\n\n".join([f"--- SOURCE: {os.path.basename(doc.metadata.get('source', 'Unknown'))} ---\n{doc.page_content}" for doc in docs])

        # Execute RAG Chain
        context_docs = retriever.invoke(question)
        context_text = format_context(context_docs)
        full_prompt = template.format(context=context_text, question=question)

        try:
            response = ollama.generate(
                model=self.model_name, prompt=full_prompt)
            return response['response']
        except Exception as e:
            return f"System Error: {str(e)}. Please ensure Ollama is running Llama 3.1."
