from flask import Flask, request, jsonify
import json
from converter import convert_document
from mongo import converted_collection


app = Flask(__name__)


@app.route("/api/convert", methods=["POST"])
def convert_api():

    try:
        # 1. Read JSON request
        data = request.get_json()

        # 2. Validate request
        if not data:
            return jsonify({
                "status": "FAILURE",
                "error": "Request body is missing"
            }), 400

        required_fields = ["requestId", "status", "documents"]

        for field in required_fields:
            if field not in data:
                return jsonify({
                    "status": "FAILURE",
                    "error": f"Missing {field}"
                }), 400

        request_id = data["requestId"]
        request_status = data["status"]

        output_documents = []

        # 3. Process every document
        for document in data["documents"]:

            # Find business type
            business_type = ""

            for item in document.get("docTypeHierarchy", []):

                if item.get("classificationName") == "CollateralType":
                    business_type = item.get("value", "").upper()
                    break

            # Business type is required for MongoDB mapping
            if not business_type:
                print(
                    f"WARNING: Business type not found for "
                    f"document {document.get('id')}"
                )
                continue

            # 4. Convert document
            converted_documents = convert_document(
                document,
                business_type,
                request_id,
                request_status
            )

            # convert_document() can return multiple documents
            output_documents.extend(converted_documents)

        # 5. Save converted documents to output.json
        with open("output.json", "w") as file:
            json.dump(
                output_documents,
                file,
                indent=2
            )

        # 6. Save converted documents to MongoDB
        if output_documents:
            converted_collection.insert_many(output_documents)

        # 7. Return API response
        response = {
            "status": "SUCCESS",
            "upload_request_id": request_id,
            "documents_converted": len(output_documents),
            "document_ids": [
                document["document_id"]
                for document in output_documents
            ]
        }

        return jsonify(response), 200

    except Exception as e:

        print(f"ERROR: {e}")

        return jsonify({
            "status": "FAILURE",
            "error": str(e)
        }), 500


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )