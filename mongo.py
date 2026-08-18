import json
from pymongo import MongoClient

Mongo_url = "mongodb://localhost:27017"

client = MongoClient(Mongo_url)
client.admin.command("ping")

db = client["json_to_json"]

# Collection for field mapping configuration
mapping_collection = db["field_transformation_config"]

# Collection for converted output documents
converted_collection = db["converted_documents"]


# Read mapping file
with open("field_mappings.json", "r") as file:
    data = json.load(file)


# Create AUTO document
auto_document = {
    "business_type": "AUTO",
    "mappings": data["autoFieldTransformationConfig"]
}


# Create MORTGAGE document
mortgage_document = {
    "business_type": "MORTGAGE",
    "mappings": data["mortgageFieldTransformationConfig"]
}


# Remove old mappings first
mapping_collection.delete_many({})


# Insert mappings
mapping_collection.insert_many([
    auto_document,
    mortgage_document
])


print("AUTO and MORTGAGE mappings inserted successfully")
print("MongoDB connected successfully!")
print("Collections:")
print("field_transformation_config")
print("converted_documents")