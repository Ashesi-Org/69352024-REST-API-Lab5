import firebase_admin
from firebase_admin import credentials, firestore

import functions_framework

import json
from flask import Flask, request, jsonify


# -------- Constant ---------------------
VOTERS_FILE = 'voters'
ELECTIONS_FILE = 'elections'
RESULTS_FILE = 'results'

STUDENT_ID = 'student_id'
ELECTION_ID = 'election_id'


# initialize firebase
firebase_admin.initialize_app()
db = firestore.client()

# initialize Flask
app = Flask(__name__)




@functions_framework.http
def api_entry(request):

    '''
    Function deployed to Google Cloud Function
    
    '''


    # GET requests
    if request.method == 'GET' and request.path == '/voters':
        return retrieve_voters()
    if request.method == 'GET' and '/voters' in request.path:
        id = request.path.split('/')[-1]
        return retrieve_voter(id)
    if request.method == 'GET' and request.path == '/elections':
        return retrieve_elections()
    if request.method == 'GET' and '/elections' in request.path:
        id = request.path.split('/')[-1]
        return retrieve_election(id)
    
    # DELETE requests
    if request.method == 'DELETE' and request.path == '/voters':
        delete_voters()
    if request.method == 'DELETE' and '/voters' in request.path:
        id = request.path.split('/')[-1]
        return delete_voter(id)
    if request.method == 'DELETE' and request.path == '/elections':
        return delete_elections()
    if request.method == 'DELETE' and 'elections' in request.path:
        id = request.path.split('/')[-1]
        return delete_election(id)
    
    # POST requests

    if request.method == 'POST' and request.path == '/elections':
        return create_election()
    if request.method == 'POST' and request.path == '/voters':
        return create_voter()
    if request.method in ['PATCH', 'PUT'] and request.path == '/voters':
        return update_voter()
    if request.method == 'POST' and request.path == '/elections/vote':
        return voting()
    return jsonify({"ERROR" : "Voter Not Found"})



 
# ---------- DB helper functions ----------   
  
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


# -------------------- VOTER ROUTES ------------------

# registering a voter
def create_voter():
    
    new_voter = json.loads(request.data)
    voters_records, wasEmpty = read_to_create(VOTERS_FILE, new_voter)
    
    # checking if the user is new
    if not wasEmpty:
        for voter in voters_records:
            if voter[STUDENT_ID] == new_voter[STUDENT_ID]:
                return jsonify({'ERROR': 'User Already Exists'}), 403
        
        voters_records.append(new_voter)
    write_to_file(VOTERS_FILE, new_voter)
    return jsonify(new_voter)

# retrieving registered voters
def retrieve_voters():

    try:
        voters_records = data_to_json(VOTERS_FILE) 
        return jsonify(voters_records)
    except:
        return jsonify({'ERROR': 'No Data Found'}), 404

# retrieeving a registered voter  
def retrieve_voter(id):

    voters_records = data_to_json(VOTERS_FILE)
    for voter in voters_records:
        if voter[STUDENT_ID] == id:
            return jsonify(voter), 200
    return jsonify({'ERROR': 'No Data Found'}), 404
        
# de-registering all registered voters
def delete_voters():

    return jsonify({'ERROR': 'Permission Denied'}), 403
    
# de-registering a registered voters
def delete_voter(student_id):

    if student_id == None: return jsonify({'ERROR': 'Permission Denied'}), 403
    deleted_voter = delete_record(VOTERS_FILE, student_id)

    if deleted_voter == None:
        return jsonify({'ERROR': 'Voter Not Found'}), 204
    return jsonify(deleted_voter), 202

# updating a registered voter
def update_voter():

    voter = json.loads(request.data)
    updated_voter = None
    new_voters_data = []
    records = data_to_json(VOTERS_FILE)
    
    # try updating
    for r in records:
        if r[STUDENT_ID] == voter[STUDENT_ID]:
            for key in voter:
                r[key] = voter[key]
            updated_voter = r
        new_voters_data.append(r)

    # add voter if not in the file
    if updated_voter == None:
        new_voters_data.append(voter)

    write_to_file(VOTERS_FILE, new_voters_data)
    return jsonify(updated_voter), 201

    
# ------------------------ ELECTION ROUTE -------------------
# creating an election
def create_election():

    new_election = json.loads(request.data)

    response_election = new_election.copy()
    
    elections_records, wasEmpty = read_to_create(ELECTIONS_FILE, new_election)

    # recording the election data
    if not wasEmpty:

        for election in elections_records:
            if election[ELECTION_ID] == new_election[ELECTION_ID]:
                return jsonify({'ERROR': 'Election Already Exists'}), 403   
        
        elections_records.append(new_election)

    # creating result for the election
    new_result = {}
    new_result[ELECTION_ID] = new_election[ELECTION_ID]
    new_result['results'] = []

    for position in  new_election['candidates']:

        for role, candidates in position.items():
            new_result['results'].append({role:{}})
            role_index = new_result['results'].index({role:{}})
            for candidate in candidates:
                new_result['results'][role_index][role][candidate] = "0"
            new_result['results'][role_index][role]['voters'] = []

    results_records, wasEmpty = read_to_create(RESULTS_FILE, new_result)
    
    if not wasEmpty: results_records.append(new_result)

    # write to both files
    write_to_file(RESULTS_FILE, new_result)
    write_to_file(ELECTIONS_FILE, new_election)
    
    return jsonify(response_election)


# retrieving an election data / all elections
def retrieve_elections():

    response_data = []
    
    results = data_to_json(RESULTS_FILE)
    elections_records = data_to_json(ELECTIONS_FILE)
    
    # combine data from results file and elections data
    for election in elections_records:
        response_entry = {}
        for res in results:
            if res[ELECTION_ID] == election[ELECTION_ID]:
                response_entry[ELECTION_ID] = res[ELECTION_ID]
                response_entry['election_name'] = election['election_name']
                response_entry['election_startdate'] = election['election_startdate']
                response_entry['election_enddate'] = election['election_enddate']
                response_entry['results'] = res['results']
        response_data.append(response_entry)
    
    # check if there is any data in the file
    if response_data == []:
        return jsonify({'ERROR': 'No Data Found'}), 404
    return jsonify(response_data)

#retrieve single election  
def retrieve_election(election_id):
    
    results = data_to_json(RESULTS_FILE)
    elections_records = data_to_json(ELECTIONS_FILE)

    # combine data from results and elections 
    for election in elections_records:
        if election[ELECTION_ID] == election_id:
            response_entry = {}
            for res in results:
                if res[ELECTION_ID] == election[ELECTION_ID]:
                    response_entry[ELECTION_ID] = res[ELECTION_ID]
                    response_entry['election_name'] = election['election_name']
                    response_entry['election_startdate'] = election['election_startdate']
                    response_entry['election_enddate'] = election['election_enddate']
                    response_entry['results'] = res['results']
                    return jsonify(response_entry)
                
    return jsonify({'ERROR': 'No Data Found'}), 404

# deleting all elections
def delete_elections():
    try:
        delete_documents(ELECTIONS_FILE)
        return jsonify({'SUCCESS': 'Deleted successfully'}), 200
    except:

        return jsonify({'ERROR': 'Permission Denied'}), 403

# delete a single election
def delete_election(election_id):

    if election_id == None: return jsonify({'ERROR': 'Permission Denied'}), 403
    delete_record(RESULTS_FILE, election_id)
    deleted_election = delete_record(ELECTIONS_FILE, election_id)

    if deleted_election == None:
        return jsonify({'ERROR': 'Election Not Found'}), 404
    return jsonify(deleted_election), 200


# voting in an election
def voting():

    voting_details = json.loads(request.data)

    response_details = voting_details.copy()

    # check voting details
    if voting_details == None: return jsonify({'ERROR': 'Permission Denied'}), 403

    if not id_checker(VOTERS_FILE, voting_details[STUDENT_ID], STUDENT_ID):
        return jsonify({'ERROR': 'Voter Not Found, Please Register'}), 404
    
    if not id_checker(ELECTIONS_FILE, voting_details[ELECTION_ID], ELECTION_ID):
        return jsonify({'ERROR': 'Election Not Found'}), 404
    
    # collect the position the user has chosen to vote for
    chosen_candidates = {}
    elections_records = data_to_json(ELECTIONS_FILE)

    for election in elections_records:

        if election[ELECTION_ID] == voting_details[ELECTION_ID]:

            for key, value in voting_details.items():

                for position in election['candidates']:
                    if key in position:
                        chosen_candidates[key] = value
                        break
    
    # # updating the results
    updated_result = None
    
    results_records = data_to_json(RESULTS_FILE)
    for result in results_records:
        if result[ELECTION_ID] == voting_details[ELECTION_ID]:
            for pos, candidate_name in chosen_candidates.items():
                
                for results_record in  result['results']:
                    
                    candidates_for_pos = results_record.get(pos)

                    # handle case when the person is voting for only one position
                    if candidates_for_pos == None:
                        continue

                    # check if the voter has not voted already
                    if voting_details[STUDENT_ID] in candidates_for_pos.get('voters'):
                        response_details[pos] = "Voted Already"
                    
                    else:
                        # check if candidate exists
                        if candidate_name not in candidates_for_pos:
                                response_details[pos] = f"{candidate_name} Not A Candidate For Position"
                                continue
                        
                        # increment the number of votes
                        candidates_for_pos[candidate_name] = int(candidates_for_pos.get(candidate_name)) + 1
                        
                        # add voter to the list of voters
                        candidates_for_pos.get('voters').append(voting_details[STUDENT_ID])
                                        
        updated_result = result
       
    # write the new results to the file
    write_to_file(RESULTS_FILE, updated_result)
    return jsonify(response_details), 200


if __name__ == '__main__':
    app.run()
