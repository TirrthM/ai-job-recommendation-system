import json
import pymongo
from config import MONGO_URI

def import_sample_data():
    client = pymongo.MongoClient(MONGO_URI)
    db = client['alumni_database']

    print("Connecting to MongoDB at:", MONGO_URI)

    # Load jobs.json
    with open('jobs.json', 'r', encoding='utf-8') as f:
        jobs_data = json.load(f)

    # Load profiles.json
    with open('profiles.json', 'r', encoding='utf-8') as f:
        profiles_data = json.load(f)

    # Clear previous collections to avoid duplicate entries
    db['jobs'].delete_many({})
    db['profiles'].delete_many({})

    # Insert data
    db['jobs'].insert_many(jobs_data)
    db['profiles'].insert_many(profiles_data)

    print(f"Successfully imported {len(jobs_data)} jobs into 'jobs' collection.")
    print(f"Successfully imported {len(profiles_data)} profiles into 'profiles' collection.")
    client.close()

if __name__ == '__main__':
    import_sample_data()
