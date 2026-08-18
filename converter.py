from mongo import db

# step 1
def convert_document(document, business_type, request_id, request_status):
    # 1. Get mapping from MongoDB
    mappings = fetch_mapping_config(business_type)

    # Convert mapping list into a  dictionary
    mapping_lookup = {
        mapping["titanFieldName"]: mapping
        for mapping in mappings
    }

    # 2. Find Object List field
    object_list_field = next(
        (
            field
            for field in document["fields"]
            if field["type"].lower() == "object list"
        ),
        None
    )

    # 3. If no Object List, create one empty group
    if object_list_field:
        groups = object_list_field["values"]
    else:
        groups = [[]]

    # 4. Convert common fields
    common_fields = []

    for field in document["fields"]:

        # Skip Object List itself
        if field is object_list_field:
            continue

        converted = convert_field(field, mapping_lookup)

        if converted:
            common_fields.append(converted)

    # 5. Create output documents
    output_documents = []

    for group_index, group in enumerate(groups):

        # Convert fields belonging to this Object List group
        group_fields = convert_object_list(
            group,
            mapping_lookup
        )

        # Build required Section 4 metadata
        metadata = build_metadata(
            document,
            request_id,
            request_status,
            group_index
        )

        # Add fields
        metadata["fields"] = common_fields + group_fields

        output_documents.append(metadata)

    return output_documents

def fetch_mapping_config(business_type):
    document = db["field_transformation_config"].find_one({
        "business_type": business_type
    })

    if not document:
        raise ValueError(
            f"No mapping configuration found for business type: {business_type}"
        )

    return document["mappings"]


def resolve_value(field):
    if field["dataType"].lower() == "dropdown":
        value_obj = field["valueObject"]
        return value_obj.get("dropdownValue", "").strip()

    return field["value"]


def convert_data_type(data_type):
    if data_type == "string":
        return "String"

    return data_type

from datetime import datetime

def parse_timestamp(value):
    if not value:
        return None

    dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S:%f")

    return {
        "$date": dt.isoformat() + "Z"
    }


def get_hierarchy_value(document, classification_name):
    for item in document.get("docTypeHierarchy", []):
        if item.get("classificationName") == classification_name:
            return item.get("value", "").upper()

    return ""


def build_metadata(
    document,
    request_id,
    request_status,
    group_index
):
    document_name = document["name"]

    if "." in document_name:
        name, extension = document_name.rsplit(".", 1)
        document_name = f"{name}_{group_index + 1}.{extension}"
    else:
        document_name = f"{document_name}_{group_index + 1}"

    # Get business type
    business_type = get_hierarchy_value(
        document,
        "CollateralType"
    )

    # Get document type
    document_type = get_hierarchy_value(
        document,
        "DocumentType"
    )

    # Check LIST_TYPE
    list_document = False

    for item in document.get("docTypeHierarchy", []):
        if item.get("classificationName") == "LIST_TYPE":
            value = item.get("value", "").upper()

            if value in ["LIST", "LIIST"]:
                list_document = True

    return {
        "upload_request_id": request_id,

        "upload_request_status": request_status,

        "document_id": document["id"],

        "document_name": document_name,

        "document_file_type": document["fileType"],

        "document_processing_status": document["status"],

        "file_uploaded_timestamp": parse_timestamp(
            document.get("lastModifiedDate")
        ),

        "document_received_timestamp": parse_timestamp(
            document.get("documentReceivedDate")
        ),

        "document_extraction_start_timestamp": parse_timestamp(
            document.get("documentExtractionStartDate")
        ),

        "business_type": business_type,

        "document_type": document_type,

        "document_page_count": len(
            document.get("pages", [])
        ),

        "original_file_page_count": 0,

        "original_file_blank_pages": document.get(
            "totalBlankPages",
            0
        ),

        "list_document": list_document,

        "optional_parameters": document.get(
            "optionalParams",
            {}
        ),

        "source_document_url": document.get(
            "sourceDocumentUrl"
        ),

        "account_id": None
    }
def convert_field(field, mapping_lookup):
    mapping = mapping_lookup.get(field["name"])

    if not mapping:
        print(f"INFO: Unmapped field skipped: {field['name']}")
        return None

    return {
        "field_name": mapping["customFormatFieldName"],
        "field_value": resolve_value(field),
        "field_type": field["type"],
        "field_data_type": convert_data_type(field["dataType"]),
    }
def convert_object_list(group, mapping_lookup):
    group_fields = []

    shared_object_id = group[0].get("objectId") if group else None

    for subfield in group:
        mapping = mapping_lookup.get(subfield["fieldName"])

        if not mapping:
            print(f"INFO: Unmapped field skipped: {subfield['fieldName']}")
            continue

        group_fields.append({
            "field_name": mapping["customFormatFieldName"],
            "field_value": resolve_value(subfield),
            "field_type": subfield["fieldType"],
            "field_data_type": convert_data_type(subfield["dataType"]),
            "titan_field_name": subfield["fieldName"],
            "titan_field_id": subfield.get("fieldId"),
            "titan_object_id": subfield.get(
                "objectId",
                shared_object_id
            )
        })

    return group_fields


if __name__ == "__main__":
    print("Converter loaded successfully!")
