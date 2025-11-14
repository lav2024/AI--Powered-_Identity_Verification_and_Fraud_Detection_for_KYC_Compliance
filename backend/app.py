from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from PIL import Image
import pytesseract
import re
import os

# ========================
# Flask App Setup
# ========================
app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ========================
# MongoDB Connection
# ========================
try:
    client = MongoClient("mongodb://localhost:27017/")
    db = client["KYCDB"]
    collection = db["extracted"]
    print("✅ MongoDB connection successful")
except Exception as e:
    print("❌ MongoDB connection failed:", e)

# ========================
# OCR and Extraction Logic
# ========================
def extract_text_from_image(image_path):
    """Extract text using Tesseract OCR"""
    text = pytesseract.image_to_string(Image.open(image_path))
    print("🔍 OCR Extracted Text:\n", text)
    return text

def extract_details(text):
    """Identify document type, extract fields, and assign fraud score"""
    extracted = {}
    fraudScore = 0

    # Helper to calculate risk after all checks
    def finalize():
        nonlocal fraudScore
        if fraudScore <= 30:
            extracted["riskLevel"] = "Low"
        elif fraudScore <= 70:
            extracted["riskLevel"] = "Medium"
        else:
            extracted["riskLevel"] = "High"

        extracted["fraudScore"] = fraudScore
        extracted["isValid"] = extracted["riskLevel"] != "High"
        return extracted

    # --------------------
    # Aadhaar Detection
    # --------------------
    aadhaar_pattern = r"\b\d{4}\s\d{4}\s\d{4}\b"
    if re.search(aadhaar_pattern, text):
        extracted["Document Type"] = "Aadhaar"

        aadhaar_match = re.search(aadhaar_pattern, text)
        name_match = re.search(r"Name[:\s]*([A-Za-z ]+)", text)
        dob_match = re.search(r"DOB[:\s]*(\d{2}/\d{2}/\d{4})", text)
        gender_match = re.search(r"\b(Male|Female|Other)\b", text, re.IGNORECASE)

        extracted["Aadhaar Number"] = aadhaar_match.group(0) if aadhaar_match else "Not Found"
        extracted["Name"] = name_match.group(1).strip() if name_match else "Not Found"
        extracted["DOB"] = dob_match.group(1) if dob_match else "Not Found"
        extracted["Gender"] = gender_match.group(1).capitalize() if gender_match else "Not Found"

        # Fraud scoring
        if extracted["Aadhaar Number"] == "Not Found":
            fraudScore += 50
        if extracted["Name"] == "Not Found":
            fraudScore += 20
        if extracted["DOB"] == "Not Found":
            fraudScore += 20

        # Duplicate check
        existing = collection.find_one({"Aadhaar Number": extracted["Aadhaar Number"]})
        if existing:
            fraudScore += 30

        return finalize()

    # --------------------
    # PAN Detection
    # --------------------
    pan_pattern = r"[A-Z]{5}[0-9]{4}[A-Z]{1}"
    if re.search(pan_pattern, text):
        extracted["Document Type"] = "PAN"

        pan_match = re.search(pan_pattern, text)
        name_match = re.search(r"Name[:\s]*([A-Za-z ]+)", text)
        father_match = re.search(r"Father'?s\s*Name[:\s]*([A-Za-z ]+)", text)

        extracted["PAN Number"] = pan_match.group(0) if pan_match else "Not Found"
        extracted["Name"] = name_match.group(1).strip() if name_match else "Not Found"
        extracted["Father's Name"] = father_match.group(1).strip() if father_match else "Not Found"

        # Fraud scoring
        if extracted["PAN Number"] == "Not Found":
            fraudScore += 50
        if extracted["Name"] == "Not Found":
            fraudScore += 20

        # Duplicate check
        existing = collection.find_one({"PAN Number": extracted["PAN Number"]})
        if existing:
            fraudScore += 30

        return finalize()

    # --------------------
    # Driving License Detection
    # --------------------
    dl_pattern = r"[A-Z]{2}\d{2}\s?\d{11}"
    if re.search(dl_pattern, text):
        extracted["Document Type"] = "Driving License"

        dl_match = re.search(dl_pattern, text)
        extracted["DL Number"] = dl_match.group(0)

        # Fraud scoring
        existing = collection.find_one({"DL Number": extracted["DL Number"]})
        if existing:
            fraudScore += 30

        return finalize()

    # --------------------
    # Unknown Document
    # --------------------
    extracted["Document Type"] = "Unknown"
    extracted["Raw Text"] = text
    fraudScore = 70  # Unknown doc is high suspicion

    return finalize()


# ========================
# Upload Route
# ========================
@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        # User entered details
        user_name = request.form.get("userName", "").lower()
        user_dob = request.form.get("userDob", "")
        user_gender = request.form.get("userGender", "").lower()

        # OCR Extract
        text = extract_text_from_image(filepath)
        extracted = extract_details(text)

        fraudScore = extracted.get("fraudScore", 0)
        reasons = extracted.get("Reasons", [])

        # Match name (simple string match)
        if extracted.get("Name", "").lower() != user_name:
            fraudScore += 25
            reasons.append("Name doesn't match user input")

        # Match DOB
        if extracted.get("DOB", "") != user_dob:
            fraudScore += 25
            reasons.append("DOB doesn't match user input")

        # Match Gender
        if extracted.get("Gender", "").lower() != user_gender:
            fraudScore += 10
            reasons.append("Gender doesn't match user input")

        # Compute risk level
        if fraudScore >= 70:
            riskLevel = "High"
        elif fraudScore >= 30:
            riskLevel = "Medium"
        else:
            riskLevel = "Low"

        extracted["fraudScore"] = fraudScore
        extracted["riskLevel"] = riskLevel
        extracted["Reasons"] = reasons

        # Save to DB
        inserted_id = collection.insert_one(extracted).inserted_id
        extracted["_id"] = str(inserted_id)

        return jsonify(extracted), 200

    except Exception as e:
        print("❌ Error in /upload route:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/records", methods=["GET"])
def get_records():
    try:
        data = list(collection.find())
        for item in data:
            item["_id"] = str(item["_id"])  # Convert ObjectId to string
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# ========================
# Run Server
# ========================
if __name__ == "__main__":
    app.run(debug=True)
