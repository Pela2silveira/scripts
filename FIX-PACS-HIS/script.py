import requests
import pymongo
import json
from pymongo import MongoClient
import os

URL = os.environ.get("URL", "https://example.com")
MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb://localhost:27017/")
DATABASE_NAME = os.environ.get("DATABASE_NAME", "nnn")
COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "nnn")
QUERY_FILENAME = os.environ.get("QUERY_FILENAME", "resources/mongodb_query.json")
OUTPUT_FILENAME = os.environ.get("OUTPUT_FILENAME", "outputs/query_response.json")
AUTH_TOKEN  = os.environ.get("AUTH_TOKEN", "xxxxx")
AUTH_CLIENT = os.environ.get("AUTH_CLIENT", "client")

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

# Main function
def main():
    while True:
        print("Menu:")
        print("1. Query MongoDB for all patients with PACS")
        print("2. Make HTTP Request")
        print("3. Quit")
        
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
            url = input("Enter the URL for the HTTP request: ")
            response = make_http_request(url)
            if response is not None:
                print(response)
        elif choice == "3":
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")


if __name__ == "__main__":
    main()
