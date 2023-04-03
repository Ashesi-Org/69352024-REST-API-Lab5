import firebase_admin
from firebase_admin import credentials, firestore

from constants import *



cred = credentials.Certificate(SERVICE_KEY_DIR)
firebase_admin.initialize_app(cred)

db = firestore.client()
    
def id_checker(filename, id, id_name):
    '''
    check if a voter/election already exists

    filename: the collection that contains the data
    id: the ide to be checked
    id_name: the field name of the id
    '''
    docs_data = [doc.to_dict() for doc in db.collection(filename).stream()]
    if len(docs_data) != 0:
        for doc in docs_data:
            if doc[id_name] == id:
                return True
    return False


def read_to_create(filename, data):
    '''
    read data and add new data if empty

    filename: name of collection to be checked
    data: the new data to be added if document is empty
    '''
    wasEmpty = False
    doc_data = [doc.to_dict() for doc in db.collection(filename).stream()]
    if len(doc_data) == 0:
        wasEmpty = True
        return ([data], wasEmpty)
    else:
        return (doc_data, wasEmpty)

def write_to_file(filename, data):
    '''
    write the give data to a firebase document

    filename: name of the collection to write to
    data: the information to be written to document
    '''
    if filename == ELECTIONS_FILE:
        db.collection(filename).document(data[ELECTION_ID]).set(data)
    if filename == RESULTS_FILE:
        db.collection(filename).document(data[ELECTION_ID]).set(data)
    if filename == VOTERS_FILE:
        db.collection(filename).document(data[STUDENT_ID]).set(data)


def data_to_json(filename):
    '''
    converting data in a collection to json format

    filename: collection to be converted
    '''
    data_from_db = [data.to_dict() for data in db.collection(filename).stream()]
    return data_from_db

def delete_record(filename, id):
    '''
    remove a document with the given id from collection, filename

    filename: name of the collection
    id: the id of the document to be removed
    '''

    deleted_record = db.collection(filename).document(id).get().to_dict()
    db.collection(filename).document(id).delete()
    return deleted_record

def delete_documents(filename):
    '''
    deleting the whole collection
    
    filename: the collection to remove
    '''
    documents = db.collection(filename).list_documents()
    for document in documents:
        document.delete()

