"""Functions to connect to a document store and fetch documents from it."""

CONFIG = {"MONGO_DATABASE": "guitar-dev", "MONGO_COLLECTION": "guitar-chat"}

def drop(collection=None, db=None, client=None):
    """Drops a collection from the database."""
    collection = get_collection(collection, db, client)

    collection.drop()

def get_collection(collection=None, db=None, client=None):
    """Accesses a specific collection in the document store."""
    import pymongo

    db = get_database(db, client)

    collection = collection or CONFIG["MONGO_COLLECTION"]

    if isinstance(collection, pymongo.collection.Collection):
        return collection
    else:
        collection = db.get_collection(collection)
        return collection

def get_database(db=None, client=None):
    """Accesses a specific database in the document store."""
    import pymongo

    client = client or connect()

    db = db or CONFIG["MONGO_DATABASE"]
    if isinstance(db, pymongo.database.Database):
        return db
    else:
        db = client.get_database(db)
        return db

def connect(user=None, password=None, uri=None):
    """Connects to the document store, here MongoDB."""
    import os
    import urllib

    import pymongo

    mongodb_user = user or os.environ["MONGODB_USER"]
    mongodb_user = urllib.parse.quote_plus(mongodb_user)

    mongodb_password = password or os.environ["MONGODB_PASSWORD"]
    mongodb_password = urllib.parse.quote_plus(mongodb_password)

    mongodb_host = uri or os.environ["MONGODB_HOST"]

    connection_string = f"mongodb+srv://{mongodb_user}:{mongodb_password}@{mongodb_host}/?retryWrites=true&w=majority"

    client = pymongo.MongoClient(connection_string, connect=True, appname="ask-fsdl")

    return client


