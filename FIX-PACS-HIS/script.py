import os
import requests
import pymongo
import json
import logging

from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime

logger = logging.getLogger("my_logger")
pymongo_logger = logging.getLogger("pymongo")

URL = os.environ.get("URL", "https://example.com")
MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb://localhost:27017/")
DATABASE_NAME = os.environ.get("DATABASE_NAME", "nnn")
COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "nnn")
QUERY_FILENAME = os.environ.get("QUERY_FILENAME", "resources/mongodb_query.json")
OUTPUT_FILENAME = os.environ.get("OUTPUT_FILENAME", "outputs/query_response.json")
GOOD_FILENAME = os.environ.get("GOOD_FILENAME", "outputs/good_response.json")
BAD_FILENAME = os.environ.get("BAD_FILENAME", "outputs/bad_response.json")
SINGLEMATCH_FILENAME = os.environ.get("SINGLEMATCH_FILENAME", "outputs/singlematch.json")
ZEROMATCH_FILENAME = os.environ.get("ZEROMATCH_FILENAME", "outputs/zeromatch.json")
MULTIMATCH_FILENAME = os.environ.get("MULTIMATCH_FILENAME", "outputs/multimatch.json")
SINGLEFIXED_FILENAME = os.environ.get("SINGLEFIXED_FILENAME", "outputs/singlefixed.json")
LOG_FILENAME = os.environ.get("LOG_FILENAME", "outputs/log.txt")

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
        return db, client
    except  pymongo.errors.ConnectionError as e:
        logger.info(f"MongoDB Connection Error: {e}")
        return None

# Function to write data to a file
def write_to_file(filename, data):
    try:
        with open(filename, "w") as file:
            file.write(data)
        logger.info(f"Data written to {filename}")
    except Exception as e:
        logger.info(f"File Writing Error: {e}")

# Function to read the MongoDB query from a JSON file
def read_mongodb_query_from_json(filename):
    try:
        with open(filename, "r") as file:
            query = json.load(file)
        return query
    except Exception as e:
        logger.info(f"JSON File Reading Error: {e}")
        return None

# Function to perform the MongoDB query
def perform_mongodb_query(db, query):
    try:
        # Perform the query
        result = list(db[COLLECTION_NAME].aggregate((query)))
        with open(OUTPUT_FILENAME, "w") as file:
            json.dump(result, file, default=str, indent=4)    
        logger.info(f"Query result written to {OUTPUT_FILENAME}")
    except Exception as e:
        logger.info(f"MongoDB Query Error: {e}")

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
        logger.info(f"Authentication Error: {e}")
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
        logger.info(f"Request Error: {e}")
        return None

def count_studies(token, patientID, modality, date, aet, host):
    url = f"{host}/dcm4chee-arc/aets/{aet}/rs/studies/count/?00100020={patientID}&00080020={date}&00080061={modality}"
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json', 'Content-Type': 'application/json'}
    try:
        response = requests.request("GET", url, headers=headers)
        response.raise_for_status() 
        return (response.json().get('count'))
    except requests.exceptions.RequestException as e:
        logger.info(f"Request Error: {e}")
        return None

def get_study(token, patientID, modality, date, aet, host):
    url = f"{host}/dcm4chee-arc/aets/{aet}/rs/studies/?00100020={patientID}&00080020={date}&00080061={modality}"
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json', 'Content-Type': 'application/json'}
    try:
        response = requests.request("GET", url, headers=headers)
        response.raise_for_status() 
        return (response.json()[0].get('0020000D').get('Value')[0])
    except requests.exceptions.RequestException as e:
        logger.info(f"Request Error: {e}")
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
        logger.info(f"File '{json_file_path}' not found.")
    except json.JSONDecodeError as e:
        logger.info(f"JSON Decoding Error: {e}")
    except Exception as e:
        logger.info(f"Error: {e}")

def try_simple_fix(filename):
    try:
        with open(filename, "r") as json_file:
            data = json.load(json_file)
            singlematch_candidates = []
            zeromatch_candidates = []
            multimatch_candidates = []
            # Iterate through each object in the array
            for item in data:
                print(".", end=" ", flush=True)
                auth_host = item.get("auth")
                host = item.get("host")
                aet = item.get("aet")
                date = convert_date(item.get("fecha"))
                modality = item.get("modalidad")
                patientID = item.get("paciente")['id']
                token = authenticate_with_keycloak(auth_host)
                response = count_studies(token, patientID, modality, date, aet, host)
                if response == 1:
                    singlematch_candidates.append(item)
                elif response == 0:
                    zeromatch_candidates.append(item)
                else:
                    multimatch_candidates.append(item)
            print("")
            print("Single match: ",len(singlematch_candidates))
            print("Zero match: ",len(zeromatch_candidates))
            print("N Match: ",len(multimatch_candidates))
            if singlematch_candidates:
                with open(SINGLEMATCH_FILENAME, "w") as singlematch_file:
                    json.dump(singlematch_candidates, singlematch_file, indent=4)
            if zeromatch_candidates:
                with open(ZEROMATCH_FILENAME, "w") as zeromatch_file:
                    json.dump(zeromatch_candidates, zeromatch_file, indent=4)
            if multimatch_candidates:
                with open(MULTIMATCH_FILENAME, "w") as multimatch_file:
                    json.dump(multimatch_candidates, multimatch_file, indent=4)
    except FileNotFoundError:
        logger.info(f"File '{json_file_path}' not found.")
    except json.JSONDecodeError as e:
        logger.info(f"JSON Decoding Error: {e}")
    except Exception as e:
        logger.info(f"Error: {e}")

def delete_object_json(json_data, id_to_delete):
    # Iterate through the list of objects and remove the one with the specified Id
    updated_data = [item for item in json_data if item.get("_id") != id_to_delete]
    return updated_data

def delete_prestacion_by_id(filename, id_to_delete):
    try:
    # Read the JSON file
        with open(filename, "r") as json_file:
            json_data = json.load(json_file)
            # Delete the object by Id
            updated_data = delete_object_json(json_data, id_to_delete)
    # Write the updated data back to the file
        with open(filename, "w") as json_file:
            json.dump(updated_data, json_file, indent=4)
        logger.info(f"Object with Id '{id_to_delete}' deleted from the JSON file.")
    except FileNotFoundError:
        logger.info(f"File '{json_file_path}' not found.")
    except json.JSONDecodeError as e:
        logger.info(f"JSON Decoding Error: {e}")
    except Exception as e:
        logger.info(f"Error: {e}")

def commit_simple_file(filename):
    try:
        with open(filename, "r") as json_file:
            data = json.load(json_file)
            singlematch_fixed = []
            # Iterate through each object in the array
            for item in data:
                print(".", end=" ", flush=True)
                auth_host = item.get("auth")
                host = item.get("host")
                aet = item.get("aet")
                date = convert_date(item.get("fecha"))
                modality = item.get("modalidad")
                patientID = item.get("paciente")['id']
                token = authenticate_with_keycloak(auth_host)
                response = get_study(token, patientID, modality, date, aet, host)
                item["fixedStudyInstanceUID"] = response
                singlematch_fixed.append(item)
            if singlematch_fixed:
                with open(SINGLEFIXED_FILENAME, "w") as singlefixed_file:
                    json.dump(singlematch_fixed, singlefixed_file, indent=4)
    except FileNotFoundError:
        logger.info(f"File '{json_file_path}' not found.")
    except json.JSONDecodeError as e:
        logger.info(f"JSON Decoding Error: {e}")
    except Exception as e:
        logger.info(f"Error: {e}")

def commit_simple_db(filename):
    db, client = connect_to_mongodb(MONGODB_URL, DATABASE_NAME)
    if db is not None:
        try:
            with open(filename, "r") as json_file:
                data = json.load(json_file)
                logger.info("Commit db: file read")
                # Rlogger.info("Commit db: file read")ead the MongoDB query from the JSON file
                for item in data:
                    prestacion_id = item.get("_id")
                    old_study_uid = item.get("studyUID")
                    new_study_uid = item.get("fixedStudyInstanceUID")
                    logger.info(f"Commit db: {prestacion_id} {old_study_uid} {new_study_uid}")
                    new_metadata_object = { "key": "old-pacs-uid", "valor": old_study_uid }
                    update_operation1_1 = {"_id": ObjectId(prestacion_id)}
                    update_operation1_2 = { "$push": { "metadata": new_metadata_object } }
                    update_operation2_1 = {"_id": ObjectId(prestacion_id), "metadata.key": "pacs-uid"}
                    update_operation2_2 = {"$set": {"metadata.$.valor": new_study_uid}}
                    try:
                        logger.info(f"Attemping to record old_study_uid: {old_study_uid} in prestación: {prestacion_id}")
                        db[COLLECTION_NAME].update_one(update_operation1_1,update_operation1_2)
                        try:
                            logger.info(f"Attemping to record new_study_uid: {new_study_uid} in prestación: {prestacion_id}")
                            db[COLLECTION_NAME].update_one(update_operation2_1,update_operation2_2)
                        except Exception as e:
                            logger.info(f"MongoDB Query Error: {e}")
                    except Exception as e:
                        logger.info(f"MongoDB Query Error: {e}")
                    delete_prestacion_by_id(filename,prestacion_id)
        except FileNotFoundError:
            logger.info(f"File '{json_file_path}' not found.")
        except json.JSONDecodeError as e:
            logger.info(f"JSON Decoding Error: {e}")
        except Exception as e:
            logger.info(f"Error: {e}")
        client.close()


def query_db():
    db, client = connect_to_mongodb(MONGODB_URL, DATABASE_NAME)
    if db is not None:
        # Read the MongoDB query from the JSON file
        mongodb_query = read_mongodb_query_from_json(QUERY_FILENAME)
        if mongodb_query:
            # Perform the MongoDB query
            perform_mongodb_query(db, mongodb_query)
        client.close()    

# Main function
def main():
    # Configure the pymongo logger to use your custom logger
    # pymongo_logger.setLevel(logging.ERROR)  # Set the log level to capture errors
    # pymongo_logger.addHandler(logging.StreamHandler())  # Capture logs to stderr

    logger.setLevel(logging.DEBUG) 
    # Create a file handler and configure it
    file_handler = logging.FileHandler(LOG_FILENAME)
    file_handler.setLevel(logging.DEBUG)  # Set the logging level for the file handler
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    # Create a console (stream) handler and configure it
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)  # Set the logging level for the console handler
    console_handler.setFormatter(formatter)
    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    while True:
        print("Menu:")
        print("1. Query MongoDB for all patients with PACS")
        print("2. Make HTTP Request")
        print("3. Try Simple Fix")
        print("4. Commit Simple Match Studies to File")
        print("5. Commit Simple Match Studies to Database - Danger!")
        print("6. Quit")
        choice = input("Enter your choice: ")
        if choice == "1":
            # Connect to MongoDB
            logger.info("Entering choice 1")
            query_db()
        elif choice == "2":
            logger.info("Entering choice 2")
            check_studies(OUTPUT_FILENAME)
        elif choice == "3":
            logger.info("Entering choice 3")
            try_simple_fix(BAD_FILENAME)   
        elif choice == "4":
            logger.info("Entering choice 4")
            commit_simple_file(SINGLEMATCH_FILENAME)     
        elif choice == "5":
            logger.info("Entering choice 5")
            print("Confirmation:")
            choice = input("Enter your choice [y/n]: ")
            if choice == "y":
                logger.info("Entering choice 5 confirmed")
                commit_simple_db(SINGLEFIXED_FILENAME)
        elif choice == "6":
            logger.info("Quiting...")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")


if __name__ == "__main__":
    main()
