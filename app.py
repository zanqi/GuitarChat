"""
Builds a CLI, Webhook, and Gradio app for Q&A on the GuitarChat corpus.

For details on corpus construction, see the accompanying notebook.
"""
import modal

import vecstore
from utils import pretty_log

image = modal.Image.debian_slim(  # we start from a lightweight linux distro
    python_version="3.10"  # we add a recent Python version
).pip_install(  # and we install the following packages:
    "langchain==0.0.184",
    # 🦜🔗: a framework for building apps with LLMs
    "openai~=0.27.7",
    # high-quality language models and cheap embeddings
    "tiktoken",
    # tokenizer for OpenAI models
    "faiss-cpu",
    # vector storage and similarity search
    "pymongo[srv]==3.11",
    # python client for MongoDB, our data persistence solution
    "gradio~=3.34",
    # simple web UIs in Python, from 🤗
    "gantry==0.5.6",
    # 🏗️: monitoring, observability, and continual improvement for ML systems
)

stub = modal.Stub(
    name="guitarchat-backend",
    image=image,
    secrets=[
        # this is where we add API keys, passwords, and URLs, which are stored on Modal
        modal.Secret.from_name("mongodb-guitar"),
        modal.Secret.from_name("openai-api-key-guitar"),
        modal.Secret.from_name("gantry-api-key-guitar"),
    ],
    mounts=[
        # we make our local modules available to the container
        modal.Mount.from_local_python_packages("docstore", "prompts")
    ],
)

VECTOR_DIR = vecstore.VECTOR_DIR
vector_storage = modal.NetworkFileSystem.persisted("vector-vol")


@stub.function(image=image)
def drop_docs(collection: str = None, db: str = None):
    """Drops a collection from the document storage."""
    import docstore

    docstore.drop(collection, db)


def prep_documents_for_vector_storage(documents):
    """Prepare documents from document store for embedding and vector storage.

    Documents are split into chunks so that they can be used with sourced Q&A.

    Arguments:
        documents: A list of LangChain.Documents with text, metadata, and a hash ID.
    """
    from langchain.text_splitter import RecursiveCharacterTextSplitter

    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=500, chunk_overlap=100, allowed_special="all"
    )
    texts, metadatas = [], []
    for document in documents:
        text, metadata = document["text"], document["metadata"]
        doc_texts = text_splitter.split_text(text)
        doc_metadatas = [metadata] * len(doc_texts)
        texts += doc_texts
        metadatas += doc_metadatas

    return texts, metadatas


@stub.function(
    image=image,
    network_file_systems={
        str(VECTOR_DIR): vector_storage,
    },
    cpu=8.0,  # use more cpu for vector storage creation
)
def create_vector_index(collection: str = None, db: str = None):
    """Creates a vector index for a collection in the document database."""
    import docstore

    pretty_log("connecting to document store")
    db = docstore.get_database(db)
    pretty_log(f"connected to database {db.name}")

    collection = docstore.get_collection(collection, db)
    pretty_log(f"collecting documents from {collection.name}")
    docs = docstore.get_documents(collection, db)

    pretty_log("splitting into bite-size chunks")
    texts, metadatas = prep_documents_for_vector_storage(docs)

    pretty_log(f"sending to vector index {vecstore.INDEX_NAME}")
    embedding_engine = vecstore.get_embedding_engine(disallowed_special=())
    vector_index = vecstore.create_vector_index(
        vecstore.INDEX_NAME, embedding_engine, texts, metadatas
    )
    vector_index.save_local(folder_path=VECTOR_DIR, index_name=vecstore.INDEX_NAME)
    pretty_log(f"vector index {vecstore.INDEX_NAME} created")


def qanda(query: str, request_id=None, with_logging: bool = False) -> str:
    from langchain.chains.qa_with_sources import load_qa_with_sources_chain
    from langchain.chat_models import ChatOpenAI

    import vecstore
    import prompts

    embedding_engine = vecstore.get_embedding_engine(allowed_special="all")

    pretty_log("connecting to vector storage")
    vector_index = vecstore.connect_to_vector_index(
        vecstore.INDEX_NAME, embedding_engine
    )
    pretty_log("connected to vector storage")
    pretty_log(f"found {vector_index.index.ntotal} vectors to search over")

    pretty_log(f"running on query: {query}")
    pretty_log("selecting sources by similarity to query")
    sources_and_scores = vector_index.similarity_search_with_score(query, k=3)
    sources, _scores = zip(*sources_and_scores)

    pretty_log("running query against Q&A chain")
    llm = ChatOpenAI(model_name="gpt-4", temperature=0, max_tokens=256)
    chain = load_qa_with_sources_chain(
        llm,
        chain_type="stuff",
        verbose=with_logging,
        prompt=prompts.main,
        document_variable_name="sources",
    )

    result = chain(
        {"input_documents": sources, "question": query}, return_only_outputs=True
    )

    answer = result["output_text"]
    return answer


@stub.function(
    image=image,
    network_file_systems={
        str(VECTOR_DIR): vector_storage,
    },
)
def cli(query: str):
    answer = qanda(query, with_logging=False)
    pretty_log("🎸 ANSWER 🎸")
    print(answer)
