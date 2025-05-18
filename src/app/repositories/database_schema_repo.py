import json
import os
from typing import Any, Dict, List, Optional

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database


class DatabaseRepository:
    def __init__(self, mongo_uri: str = "mongodb://localhost:27017/"):
        self.client = MongoClient(mongo_uri)

    def initialize_db_from_repo_path(self, repo_path: str) -> Database:
        # Extract repository name from the path
        repo_name = os.path.basename(repo_path.rstrip("/"))
        # Initialize database with repository name
        db = self.client[repo_name]
        return db

    def create_collection(
        self, db: Database, collection_name: str
    ) -> Collection:
        return db[collection_name]

    def insert_one(self, collection: Collection, data: Dict[str, Any]) -> str:
        result = collection.insert_one(data)
        return str(result.inserted_id)

    def insert_many(
        self, collection: Collection, data_list: List[Dict[str, Any]]
    ) -> List[str]:
        result = collection.insert_many(data_list)
        return [str(id) for id in result.inserted_ids]

    def find_one(
        self, collection: Collection, query: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        result = collection.find_one(query)
        return result

    def find_many(
        self, collection: Collection, query: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        cursor = collection.find(query)
        return list(cursor)

    def update_one(
        self,
        collection: Collection,
        query: Dict[str, Any],
        update_data: Dict[str, Any],
    ) -> int:
        result = collection.update_one(query, {"$set": update_data})
        return result.modified_count

    def delete_one(self, collection: Collection, query: Dict[str, Any]) -> int:
        result = collection.delete_one(query)
        return result.deleted_count

    def insert_data_from_json(
        self, repo_path: str, json_path: str, collection_name: str
    ) -> List[str]:
        # Initialize database from repository path
        db = self.initialize_db_from_repo_path(repo_path)

        # Create collection
        collection = self.create_collection(db, collection_name)

        # Load data from JSON file
        with open(json_path, "r") as f:
            data = json.load(f)

        # Handle both single document and list of documents
        if isinstance(data, list):
            return self.insert_many(collection, data)
        else:
            return [self.insert_one(collection, data)]
