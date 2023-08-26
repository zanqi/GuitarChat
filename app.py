"""
Builds a CLI, Webhook, and Gradio app for Q&A on the GuitarChat corpus.

For details on corpus construction, see the accompanying notebook.
"""
from typing import Optional
from fastapi.responses import RedirectResponse
import modal
from fastapi import FastAPI

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
def drop_docs(collection: Optional[str] = None, db: Optional[str] = None):
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
def create_vector_index(
    collectionName: Optional[str] = None, dbName: Optional[str] = None
):
    """Creates a vector index for a collection in the document database."""
    import docstore

    pretty_log("connecting to document store")
    db = docstore.get_database(dbName)
    pretty_log(f"connected to database {db.name}")

    collection = docstore.get_collection(collectionName, db)
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
    llm = ChatOpenAI(model="gpt-4", temperature=0, max_tokens=256)
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


web_app = FastAPI(docs_url=None)


@web_app.get("/", response_class=RedirectResponse, status_code=308)
async def root():
    return "/gradio"


@web_app.get("/docs", response_class=RedirectResponse, status_code=308)
async def redirect_docs():
    """Redirects to the Gradio subapi docs."""
    return "/gradio/docs"


@stub.function(
    image=image,
    network_file_systems={
        str(VECTOR_DIR): vector_storage,
    },
    keep_warm=1,
)
@modal.asgi_app(label="guitarchat-backend")
def fastapi_app():
    """A simple Gradio interface for debugging."""
    import gradio as gr
    from gradio.routes import App

    def chain_with_logging(*args, **kwargs):
        return qanda(*args, with_logging=True, **kwargs)

    def chat_fn(message, history):
        return qanda(message, with_logging=True)

    textbox = gr.inputs.Textbox(lines=2, placeholder="How to play the D chord?")

    # inputs = gr.TextArea(
    #     label="Question",
    #     value="How to play the D chord?",
    #     show_label=True,
    # )
    # outputs = gr.TextArea(
    #     label="Answer", value="The answer will appear here.", show_label=True
    # )

    interface = gr.ChatInterface(
        fn=chat_fn,
        textbox=textbox,
        title="Ask Questions About guitar playing.",
        description="Get answers with sources from an LLM.",
        examples=[
            "How to tune my guitar?",
            "How to strum on time?",
            "Can you give me some easy songs involving only chords A, D, E?",
            "How to read guitar tabs?",
            "What is the 16th note strumming pattern?",
            "Any tips for faster chord changes?",
            "What is the best way to learn guitar?",
        ],
        theme=gr.themes.Default(radius_size="none", text_size="lg"),
    )

    # interface = gr.Interface(
    #     fn=chain_with_logging,
    #     inputs=inputs,
    #     outputs=outputs,
    #     title="Ask Questions About guitar playing.",
    #     description="Get answers with sources from an LLM.",
    #     examples=[
    #         "How to tune my guitar?",
    #         "How to strum on time?",
    #         "Can you give me some easy songs involving only chords A, D, E?",
    #         "How to read guitar tabs?",
    #         "What is the 16th note strumming pattern?",
    #         "Any tips for faster chord changes?",
    #         "What is the best way to learn guitar?",
    #     ],
    #     allow_flagging="never",
    #     theme=gr.themes.Default(radius_size="none", text_size="lg"),
    # )

    interface.dev_mode = False
    interface.config = interface.get_config_file()
    interface.validate_queue_settings()
    gradio_app = App.create_app(
        interface, app_kwargs={"docs_url": "/docs", "title": "GuitarChat"}
    )

    @web_app.on_event("startup")
    async def start_queue():
        if gradio_app.get_blocks().enable_queue:
            gradio_app.get_blocks().startup_events()

    web_app.mount("/gradio", gradio_app)

    return web_app
