import os
import requests
import pymongo
import json
from pymongo import MongoClient
from datetime import datetime



URL = os.environ.get("URL", "https://example.com")
MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb://localhost:27017/")
DATABASE_NAME = os.environ.get("DATABASE_NAME", "nnn")
COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "nnn")
QUERY_FILENAME = os.environ.get("QUERY_FILENAME", "resources/mongodb_query.json")
OUTPUT_FILENAME = os.environ.get("OUTPUT_FILENAME", "outputs/query_response.json")
GOOD_FILENAME = os.environ.get("OUTPUT_FILENAME", "outputs/good_response.json")
BAD_FILENAME= os.environ.get("OUTPUT_FILENAME", "outputs/bad_response.json")
AUTH_TOKEN  = os.environ.get("AUTH_TOKEN", "xxxxx")
AUTH_CLIENT = os.environ.get("AUTH_CLIENT", "client")

def convert_date(date):
    # Input date format "2021-04-23 15:18:55.921000"
    #cut miliseconds
    newdate=date.split('.')[0]
    # Parse the input date string into a datetime object
    input_date = datetime.strptime(newdate, "%Y-%m-%d %H:%M:%S")
    
    # Format the datetime object to the desired output format
    return (input_date.strftime("%Y%m%d"))

# Function to make an HTTP GET request
def make_http_request(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"HTTP Request Error: {e}")
        return None

# Function to connect to a MongoDB database
def connect_to_mongodb(database_url, database_name):
    try:
        client = MongoClient(database_url)
        db = client[database_name]
        return db
    except Exception as e:
        print(f"MongoDB Connection Error: {e}")
        return None

# Function to write data to a file
def write_to_file(filename, data):
    try:
        with open(filename, "w") as file:
            file.write(data)
        print(f"Data written to {filename}")
    except Exception as e:
        print(f"File Writing Error: {e}")

# Function to read the MongoDB query from a JSON file
def read_mongodb_query_from_json(filename):
    try:
        with open(filename, "r") as file:
            query = json.load(file)
        return query
    except Exception as e:
        print(f"JSON File Reading Error: {e}")
        return None

# Function to perform the MongoDB query
def perform_mongodb_query(db, query):
    try:
        # Perform the query
        result = list(db[COLLECTION_NAME].aggregate((query)))
        with open(OUTPUT_FILENAME, "w") as file:
            json.dump(result, file, default=str, indent=4)    
        print(f"Query result written to {OUTPUT_FILENAME}")
    except Exception as e:
        print(f"MongoDB Query Error: {e}")

def authenticate_with_keycloak(keycloak_host):
    token_url = f"{keycloak_host}/auth/realms/dcm4che/protocol/openid-connect/token"
    # Prepare the payload for the request
    payload = f"grant_type=client_credentials&client_id={AUTH_CLIENT}&client_secret={AUTH_TOKEN}"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    try:
        # Make a POST request to obtain the access token
        #response = requests.post(token_url, data=data, headers=headers)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        response = requests.request("POST", token_url, headers=headers, data=payload)
        response.raise_for_status()  # Raise an exception for HTTP errors
        #print(response.json().get('access_token'))
        # Parse the JSON response and extract the access token
        access_token = response.json().get('access_token')
        return access_token
    except requests.exceptions.RequestException as e:
        print(f"Authentication Error: {e}")
        return None

def exists_study(token, studyUID, aet, host):
    url = f"{host}/dcm4chee-arc/aets/{aet}/rs/studies/?StudyInstanceUID={studyUID}"
    payload={}
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/dicom+json'}
    try:
        response = requests.request("GET", url, headers=headers, data=payload)
        response.raise_for_status() 
        return (response.status_code==200)
    except requests.exceptions.RequestException as e:
        print(f"Request Error: {e}")
        return None

def count_studies(token, patientID, modality, date, aet, host):
    url = f"{host}/dcm4chee-arc/aets/{aet}/rs/studies/count/?00100020={patientID}&00080020={date}&00080061={modality}"
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json', 'Content-Type': 'application/json'}
    try:
        response = requests.request("GET", url, headers=headers)
        response.raise_for_status() 
        return (response.json().get('count'))
    except requests.exceptions.RequestException as e:
        print(f"Request Error: {e}")
        return None

def check_studies(filename):
    try:
        with open(filename, "r") as json_file:
            data = json.load(json_file)
            good_responses = []
            bad_responses = []
            # Iterate through each object in the array
            for item in data:
                study_uid = item.get("studyUID")
                auth_host = item.get("auth")
                host = item.get("host")
                aet = item.get("aet")
                if study_uid is not None:
                    token = authenticate_with_keycloak(auth_host)
                    response = exists_study(token,study_uid,aet,host)
                    if response:
                        good_responses.append(item)
                    else:
                        bad_responses.append(item)
                else:
                    print("Study UID not found in the object")
                    # Add items to "outputs/good_response.json"
            if good_responses:
                with open(GOOD_FILENAME, "w") as good_file:
                    json.dump(good_responses, good_file, indent=4)
            # Add items to "outputs/bad_response.json"
            if bad_responses:
                with open(BAD_FILENAME, "w") as bad_file:
                    json.dump(bad_responses, bad_file, indent=4)
            print("Bad studies: ",len(bad_responses))
            print("Good studies: ",len(good_responses))
            print("Efectividad: ",len(good_responses)/(len(good_responses)+len(bad_responses)) )
    except FileNotFoundError:
        print(f"File '{json_file_path}' not found.")
    except json.JSONDecodeError as e:
        print(f"JSON Decoding Error: {e}")
    except Exception as e:
        print(f"Error: {e}")

def try_simple_fix(filename):
    try:
        with open(filename, "r") as json_file:
            data = json.load(json_file)
            simple_candidates = []
            zeromatch_candidates = []
            nmatch_candidates = []
            # Iterate through each object in the array
            for item in data:
                auth_host = item.get("auth")
                host = item.get("host")
                aet = item.get("aet")
                date = convert_date(item.get("fecha"))
                modality = item.get("modalidad")
                patientID = item.get("paciente")['id']
                token = authenticate_with_keycloak(auth_host)
                response = count_studies(token, patientID, modality, date, aet, host)
                print(response)
                    # if response:
                    #     simple_candidates.append(item)
                    # else:
                    #     bad_responses.append(item)
                    # Add items to "outputs/good_response.json"
            # if good_responses:
            #     with open(GOOD_FILENAME, "w") as good_file:
            #         json.dump(good_responses, good_file, indent=4)
            # # Add items to "outputs/bad_response.json"
            # if bad_responses:
            #     with open(BAD_FILENAME, "w") as bad_file:
            #         json.dump(bad_responses, bad_file, indent=4)
            # print("Bad studies: ",len(bad_responses))
            # print("Good studies: ",len(good_responses))
            # print("Efectividad: ",len(good_responses)/(len(good_responses)+len(bad_responses)) )
    except FileNotFoundError:
        print(f"File '{json_file_path}' not found.")
    except json.JSONDecodeError as e:
        print(f"JSON Decoding Error: {e}")
    except Exception as e:
        print(f"Error: {e}")

# Main function
def main():
    while True:
        print("Menu:")
        print("1. Query MongoDB for all patients with PACS")
        print("2. Make HTTP Request")
        print("3. Try Simple Fix")
        print("4. Quit")
        choice = input("Enter your choice: ")
        if choice == "1":
            # Connect to MongoDB
            db = connect_to_mongodb(MONGODB_URL, DATABASE_NAME)
            if db is not None:
                # Read the MongoDB query from the JSON file
                mongodb_query = read_mongodb_query_from_json(QUERY_FILENAME)
                if mongodb_query:
                    # Perform the MongoDB query
                    perform_mongodb_query(db, mongodb_query)
        elif choice == "2":
            check_studies(OUTPUT_FILENAME)
        elif choice == "3":
            try_simple_fix(BAD_FILENAME)            
        elif choice == "4":
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")


if __name__ == "__main__":
    main()
