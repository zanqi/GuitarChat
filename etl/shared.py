import modal

image = modal.Image.debian_slim(python_version="3.10").pip_install(
    "langchain~=0.0.98", "pymongo[srv]==3.11"
)

stub = modal.Stub(
    name="etl-shared",
    secrets=[
        modal.Secret.from_name("mongodb-guitar"),
    ],
    mounts=[
        # we make our local modules available to the container
        modal.Mount.from_local_python_packages("docstore")
    ],
)


def flatten(list_of_lists):
    # """Recombines a list of lists into a single list."""
    return [
        item
        for sublist in list_of_lists
        if not isinstance(sublist, Exception)
        for item in sublist
    ]


def chunk_into(list, n_chunks):
    """Splits list into n_chunks pieces, non-contiguously."""
    for i in range(0, n_chunks):
        yield list[i::n_chunks]


@stub.function(image=image)
def add_to_document_db(documents_json, collection=None, db=None):
    """Adds a collection of json documents to a database."""
    from pymongo import InsertOne

    import docstore

    collection = docstore.get_collection(collection, db)

    requesting, CHUNK_SIZE = [], 250

    for document in documents_json:
        requesting.append(InsertOne(document))

        if len(requesting) >= CHUNK_SIZE:
            collection.bulk_write(requesting)
            requesting = []

    if requesting:
        collection.bulk_write(requesting)
