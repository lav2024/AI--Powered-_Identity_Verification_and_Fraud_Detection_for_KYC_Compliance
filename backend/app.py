from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pymongo import MongoClient
from PIL import Image
import pytesseract
import re
import os
import difflib
from datetime import datetime
from bson import ObjectId
import io
import csv
import traceback

app = Flask(__name__)
CORS(app)

# --- configuration ---
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

MONGO_URI = "mongodb://localhost:27017/"   # change if needed
DB_NAME = "KYCDB"

# --- MongoDB client / collections ---
client = MongoClient(MONGO_URI)
db = client[DB_NAME]

collection = db["extracted"]                 # pending uploads
approved_collection = db["approved_records"] # admin approved
rejected_collection = db["rejected_records"] # admin rejected
aml_collection = db["aml_alerts"]            # AML alerts store
blacklist_collection = db["blacklist"]       # blacklist store

# --- Helpers: OCR / text extraction ---
def extract_text_from_image(image_path):
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
    except Exception as e:
        print("OCR error:", e)
        text = ""
    text = "\n".join([ln.strip() for ln in text.splitlines() if ln.strip()])
    return text

# --- Loose / robust extraction helpers ---
def find_name_loose(text):
    if not text:
        return None
    # look for explicit label
    m = re.search(r"(?:Name|Naam|नाम)[:\s\-]*([A-Za-z][A-Za-z\s\.\-]{1,120})", text, re.IGNORECASE)
    if m:
        cand = m.group(1).strip()
        cand = re.split(r"\s{2,}|,|DOB|D\.O\.B|Father|S\/O|S\.O\.", cand, maxsplit=1)[0].strip()
        return cand
    # a few heuristics on first lines
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for ln in lines[:10]:
        if re.match(r"^[A-Z][a-z]+(?:\s[A-Z][a-z]+)+$", ln):
            return ln
        if re.match(r"^[A-Z\s]{3,}$", ln) and len(ln.split()) >= 2:
            return ln.title()
    for ln in lines[:12]:
        if re.match(r"^[A-Za-z][A-Za-z\s\.'\-]{3,}$", ln) and len(ln.split()) >= 2:
            return ln
    return None

def find_father_name_loose(text):
    if not text:
        return None
    m = re.search(r"(?:Father|Father's Name|FATHER|S\/O|S\.O\.|Shri)[:\s\-]*([A-Za-z][A-Za-z\s\.\-]{2,80})", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r"\b(?:S\/O|D\/O|Son of|Daughter of)\s+([A-Za-z][A-Za-z\s\.\-]{2,80})", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None

def normalize_date_string(s):
    s = (s or "").strip()
    parts = re.split(r"[-/\.]", s)
    if len(parts) == 3:
        # handle yyyy-mm-dd and dd-mm-yyyy
        if len(parts[0]) == 4:
            yyyy, mm, dd = parts
        else:
            dd, mm, yyyy = parts
        if len(yyyy) == 2:
            yy = int(yyyy)
            yyyy = f"19{yyyy}" if yy > 30 else f"20{yyyy}"
        try:
            return f"{str(int(dd)).zfill(2)}/{str(int(mm)).zfill(2)}/{int(yyyy)}"
        except:
            return s
    return s

def find_dob_loose(text):
    if not text:
        return None
    m = re.search(r"(?:DOB|D\.O\.B|Date of Birth|Birth)[:\s\-]*([0-9]{1,4}[-/\.][0-9]{1,2}[-/\.][0-9]{2,4})", text, re.IGNORECASE)
    if m:
        return normalize_date_string(m.group(1))
    m = re.search(r"([0-9]{2}[-/\.][0-9]{2}[-/\.][0-9]{4})", text)
    if m:
        return normalize_date_string(m.group(1))
    return None

def find_gender_loose(text):
    if not text:
        return None
    m = re.search(r"\b(Male|Female|Other|M|F)\b", text, re.IGNORECASE)
    if not m:
        return None
    g = m.group(1).lower()
    if g in ("m", "male"):
        return "Male"
    if g in ("f", "female"):
        return "Female"
    return "Other"

# --- Patterns for document numbers ---
AADHAAR_SPACED = re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b")
AADHAAR_CONTIG = re.compile(r"\b\d{12}\b")
PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE)
DL_PATTERN = re.compile(r"\b[A-Z]{2}\d{2}\s?\d{6,12}\b", re.IGNORECASE)

def extract_details_from_text(text):
    out = {
        "Document Type": "Unknown",
        "Name": None,
        "FatherName": None,
        "DOB": None,
        "Gender": None,
        "number": None,
        "fraudScore": 30,
        "reasons": []
    }
    if not text:
        out["reasons"].append("No OCR text")
        out["fraudScore"] = 80
        return out

    m = AADHAAR_SPACED.search(text) or AADHAAR_CONTIG.search(text)
    if m:
        digits = re.sub(r"\D", "", m.group(0))
        if len(digits) >= 12:
            out["Document Type"] = "Aadhaar"
            out["number"] = f"{digits[:4]} {digits[4:8]} {digits[8:12]}"
        else:
            out["number"] = m.group(0)
        out["Name"] = find_name_loose(text)
        out["FatherName"] = find_father_name_loose(text)
        out["DOB"] = find_dob_loose(text)
        out["Gender"] = find_gender_loose(text)
        out["fraudScore"] = 10
        return out

    m = PAN_PATTERN.search(text)
    if m:
        out["Document Type"] = "PAN"
        out["number"] = m.group(0).upper()
        out["Name"] = find_name_loose(text)
        out["FatherName"] = find_father_name_loose(text)
        out["fraudScore"] = 15
        return out

    m = DL_PATTERN.search(text)
    if m:
        out["Document Type"] = "Driving Licence"
        out["number"] = m.group(0).upper()
        out["Name"] = find_name_loose(text)
        out["FatherName"] = find_father_name_loose(text)
        out["DOB"] = find_dob_loose(text)
        out["fraudScore"] = 20
        return out

    out["reasons"].append("Document not recognized")
    out["fraudScore"] = 80
    return out

def similarity(a, b):
    if not a or not b:
        return 0.0
    try:
        return difflib.SequenceMatcher(None, str(a).lower().strip(), str(b).lower().strip()).ratio()
    except:
        return 0.0

# --- AML helpers ---
def check_blacklist_for_number(num):
    if not num:
        return False
    return blacklist_collection.find_one({"number": {"$regex": f"^{re.escape(str(num))}$", "$options": "i"}}) is not None

def find_duplicate_number(num):
    if not num:
        return []
    query = {"documents.number": {"$regex": re.escape(str(num)), "$options": "i"}}
    found_pending = list(collection.find(query))
    found_approved = list(approved_collection.find(query))
    found_rejected = list(rejected_collection.find(query))
    return found_pending + found_approved + found_rejected

# -----------------------
# /upload endpoint - main processing pipeline
# -----------------------
@app.route("/upload", methods=["POST"])
def upload():
    try:
        user_name = (request.form.get("userName") or "").strip()
        user_dob = (request.form.get("userDob") or "").strip()   # expected DD/MM/YYYY from frontend
        user_gender = (request.form.get("userGender") or "").strip().lower()

        documents = []
        overall_reasons = []
        aml_alerts_for_record = []

        fields = [("aadhar", "Aadhaar"), ("pan", "PAN"), ("dl", "Driving Licence")]

        for field_key, label in fields:
            f = request.files.get(field_key)
            if not f:
                continue

            filename = f.filename
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            f.save(filepath)

            text = extract_text_from_image(filepath)
            extracted = extract_details_from_text(text)

            detected = extracted.get("Document Type") == label

            # name similarity
            if extracted.get("Name") and user_name:
                sim = similarity(extracted["Name"], user_name)
                extracted["match"] = round(sim, 3)
                if sim < 0.6:
                    extracted["fraudScore"] += 25
                    extracted["reasons"].append("Name similarity low vs user input")
                else:
                    extracted["fraudScore"] = max(0, extracted["fraudScore"] - 5)
            else:
                extracted["match"] = 0.0

            # DOB checks
            if user_dob:
                if extracted.get("DOB"):
                    if extracted.get("DOB") != user_dob:
                        extracted["fraudScore"] += 25
                        extracted["reasons"].append("DOB mismatch vs user input")
                else:
                    extracted["fraudScore"] += 10
                    extracted["reasons"].append("DOB not found on document")

            # Gender check
            if user_gender:
                doc_gender = (extracted.get("Gender") or "").lower()
                if doc_gender and doc_gender != user_gender:
                    extracted["fraudScore"] += 10
                    extracted["reasons"].append("Gender mismatch vs user input")

            # Blacklist check
            docnum = extracted.get("number")
            if docnum and check_blacklist_for_number(docnum):
                extracted["fraudScore"] += 50
                extracted["reasons"].append("Document number is blacklisted (AML)")
                aml_alerts_for_record.append({
                    "type": "Blacklisted Number",
                    "number": docnum,
                    "reason": "Number exists in blacklist"
                })

            # Duplicate number check
            dup_found = find_duplicate_number(docnum)
            if docnum and dup_found:
                # if there are other records with same number (could be pending/approved/rejected)
                extracted["fraudScore"] += 40
                extracted["reasons"].append("Duplicate document number detected in DB (possible synthetic identity / reuse)")
                aml_alerts_for_record.append({
                    "type": "Duplicate Number",
                    "number": docnum,
                    "matches": [str(r.get("_id")) for r in dup_found][:8]
                })

            doc_obj = {
                "type": label,
                "filename": filename,
                "detected": bool(detected),
                "Name": extracted.get("Name"),
                "FatherName": extracted.get("FatherName"),
                "DOB": extracted.get("DOB"),
                "Gender": extracted.get("Gender"),
                "number": extracted.get("number"),
                "fraudScore": int(extracted.get("fraudScore", 0)),
                "riskLevel": "High" if extracted.get("fraudScore", 0) >= 70 else ("Medium" if extracted.get("fraudScore", 0) >= 30 else "Low"),
                "match": round(extracted.get("match", 0), 3),
                "reasons": extracted.get("reasons", [])
            }

            documents.append(doc_obj)
            overall_reasons += extracted.get("reasons", [])

        if not documents:
            return jsonify({"error": "No documents uploaded"}), 400

        overall_score = int(round(sum(d["fraudScore"] for d in documents) / len(documents)))
        overall_risk = "High" if overall_score >= 70 else ("Medium" if overall_score >= 30 else "Low")

        # Final decision rule (simple, adjustable)
        final_status = "Auto-Pass"
        if overall_risk == "Medium":
            final_status = "Review"
        if overall_risk == "High" or (len(aml_alerts_for_record) > 0):
            final_status = "Flagged"

        aml_entry_id = None
        if aml_alerts_for_record:
            aml_doc = {
                "alerts": aml_alerts_for_record,
                "created_at": datetime.utcnow().isoformat(),
                "userName": user_name,
                "documents_sample": documents[:3]
            }
            res = aml_collection.insert_one(aml_doc)
            aml_entry_id = str(res.inserted_id)

        record = {
            "userName": user_name,
            "userDob": user_dob,
            "userGender": user_gender,
            "documents": documents,
            "overallFraudScore": overall_score,
            "overallRiskLevel": overall_risk,
            "finalStatus": final_status,
            "amlAlerts": aml_alerts_for_record,
            "amlEntryId": aml_entry_id,
            "reasons": list(dict.fromkeys(overall_reasons)),
            "status": "Pending",
            "adminStatus": None,
            "timestamp": datetime.utcnow().isoformat()
        }

        inserted = collection.insert_one(record)
        record["_id"] = str(inserted.inserted_id)

        print(f"[UPLOAD] saved record {record['_id']} finalStatus={final_status} overallRisk={overall_risk}")
        return jsonify(record), 200

    except Exception as e:
        print("❌ /upload error:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# -----------------------
# /records: return pending
# -----------------------
@app.route("/records", methods=["GET"])
def get_records():
    try:
        data = list(collection.find({"status": "Pending"}).sort([("_id", -1)]).limit(500))
        out = []
        for d in data:
            d["_id"] = str(d["_id"])
            out.append(d)
        return jsonify(out), 200
    except Exception as e:
        print("❌ /records error:", e)
        return jsonify({"error": str(e)}), 500

# -----------------------
# /review/<id> : generic admin review endpoint (accepts JSON {status: "Approved"|"Rejected", adminUser: "name"})
# -----------------------
@app.route("/review/<id>", methods=["POST"])
def review(id):
    try:
        info = request.get_json() or {}
        status = info.get("status")
        admin_user = info.get("adminUser", "admin")

        if status not in ("Approved", "Rejected"):
            return jsonify({"error": "status must be Approved or Rejected"}), 400

        rec = collection.find_one({"_id": ObjectId(id)})
        if not rec:
            return jsonify({"error": "Record not found"}), 404

        rec["adminStatus"] = status
        rec["adminAction"] = {"by": admin_user, "at": datetime.utcnow().isoformat()}
        rec["status"] = status

        if status == "Approved":
            approved_collection.insert_one(rec)
        else:
            rejected_collection.insert_one(rec)

        collection.delete_one({"_id": ObjectId(id)})

        print(f"[REVIEW] record {id} -> {status} by {admin_user}")
        return jsonify({"message": f"Record {status}"}), 200

    except Exception as e:
        print("❌ /review error:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# -----------------------
# backward-compatible approve/reject endpoints
# -----------------------
@app.route("/approve/<id>", methods=["POST"])
def approve(id):
    try:
        rec = collection.find_one({"_id": ObjectId(id)})
        if not rec:
            return jsonify({"error": "Record not found"}), 404
        rec["status"] = "Approved"
        rec["adminStatus"] = "Approved"
        rec["adminAction"] = {"by": "admin", "at": datetime.utcnow().isoformat()}
        approved_collection.insert_one(rec)
        collection.delete_one({"_id": ObjectId(id)})
        print(f"[APPROVE] {id}")
        return jsonify({"message": "Approved"}), 200
    except Exception as e:
        print("❌ /approve error:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/reject/<id>", methods=["POST"])
def reject(id):
    try:
        rec = collection.find_one({"_id": ObjectId(id)})
        if not rec:
            return jsonify({"error": "Record not found"}), 404
        rec["status"] = "Rejected"
        rec["adminStatus"] = "Rejected"
        rec["adminAction"] = {"by": "admin", "at": datetime.utcnow().isoformat()}
        rejected_collection.insert_one(rec)
        collection.delete_one({"_id": ObjectId(id)})
        print(f"[REJECT] {id}")
        return jsonify({"message": "Rejected"}), 200
    except Exception as e:
        print("❌ /reject error:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# -----------------------
# alerts endpoints
# -----------------------
@app.route("/alerts", methods=["GET"])
def alerts():
    try:
        data = list(collection.find({"overallRiskLevel": "High"}))
        out = []
        for d in data:
            d["_id"] = str(d["_id"])
            out.append(d)
        return jsonify(out), 200
    except Exception as e:
        print("❌ /alerts error:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/alerts/aml", methods=["GET"])
def aml_alerts():
    try:
        data = list(aml_collection.find())
        out = []
        for d in data:
            d["_id"] = str(d["_id"])
            out.append(d)
        return jsonify(out), 200
    except Exception as e:
        print("❌ /alerts/aml error:", e)
        return jsonify({"error": str(e)}), 500

# -----------------------
# audit trail endpoint
# -----------------------
@app.route("/audit_trail", methods=["GET"])
def audit_trail():
    try:
        risk = request.args.get("risk")
        name = request.args.get("name")
        num = request.args.get("number")

        query = {}
        if risk:
            query["overallRiskLevel"] = risk
        if name:
            query["userName"] = {"$regex": name, "$options": "i"}
        if num:
            query["documents.number"] = {"$regex": num, "$options": "i"}

        data = list(approved_collection.find(query)) + list(rejected_collection.find(query))
        out = []
        for d in data:
            d["_id"] = str(d["_id"])
            out.append(d)
        return jsonify(out), 200
    except Exception as e:
        print("❌ /audit_trail error:", e)
        return jsonify({"error": str(e)}), 500

# -----------------------
# blacklist CRUD
# -----------------------
@app.route("/blacklist", methods=["GET", "POST", "DELETE"])
def blacklist():
    try:
        if request.method == "GET":
            data = list(blacklist_collection.find())
            out = []
            for d in data:
                d["_id"] = str(d["_id"])
                out.append(d)
            return jsonify(out), 200

        if request.method == "POST":
            info = request.get_json() or {}
            entry = {"type": info.get("type"), "number": info.get("number"), "added_at": datetime.utcnow().isoformat()}
            res = blacklist_collection.insert_one(entry)
            entry["_id"] = str(res.inserted_id)
            print(f"[BLACKLIST ADD] {entry}")
            return jsonify(entry), 201

        if request.method == "DELETE":
            info = request.get_json() or {}
            num = info.get("number")
            res = blacklist_collection.delete_many({"number": num})
            return jsonify({"deleted": res.deleted_count}), 200
    except Exception as e:
        print("❌ /blacklist error:", e)
        return jsonify({"error": str(e)}), 500

# -----------------------
# all-records for dashboard
# -----------------------
@app.route("/all-records", methods=["GET"])
def all_records():
    def safe_ts(val):
        if isinstance(val, datetime):
            return val
        if isinstance(val, str):
            try:
                return datetime.fromisoformat(val)
            except:
                return datetime.min
        return datetime.min

    output = []

    # pending
    pending = list(collection.find())
    for r in pending:
        r["_id"] = str(r["_id"])
        r["source"] = "Pending"
        output.append(r)

    # approved
    approved = list(approved_collection.find())
    for r in approved:
        r["_id"] = str(r["_id"])
        r["source"] = "Approved"
        output.append(r)

    # rejected
    rejected = list(rejected_collection.find())
    for r in rejected:
        r["_id"] = str(r["_id"])
        r["source"] = "Rejected"
        output.append(r)

    # FIXED SORT
    output.sort(key=lambda x: safe_ts(x.get("timestamp")), reverse=True)

    return jsonify(output), 200


# -----------------------
# CSV export
# /export_csv?type=all|approved|rejected|alerts
# -----------------------
@app.route("/export_csv", methods=["GET"])
def export_csv():
    try:
        t = request.args.get("type", "all")
        rows = []
        headers = []

        if t == "alerts":
            data = list(aml_collection.find())
            headers = ["aml_id", "created_at", "userName", "alert_type", "number", "matches"]
            for d in data:
                for a in d.get("alerts", []):
                    rows.append({
                        "aml_id": str(d.get("_id")),
                        "created_at": d.get("created_at"),
                        "userName": d.get("userName"),
                        "alert_type": a.get("type"),
                        "number": a.get("number"),
                        "matches": ",".join(a.get("matches", [])) if a.get("matches") else ""
                    })
        else:
            if t == "approved":
                data = list(approved_collection.find())
            elif t == "rejected":
                data = list(rejected_collection.find())
            else:
                data = list(collection.find()) + list(approved_collection.find()) + list(rejected_collection.find())

            headers = ["record_id", "userName", "overallFraudScore", "overallRiskLevel", "finalStatus", "status", "timestamp", "documents_summary"]
            for d in data:
                rows.append({
                    "record_id": str(d.get("_id")),
                    "userName": d.get("userName"),
                    "overallFraudScore": d.get("overallFraudScore"),
                    "overallRiskLevel": d.get("overallRiskLevel"),
                    "finalStatus": d.get("finalStatus"),
                    "status": d.get("status"),
                    "timestamp": d.get("timestamp"),
                    "documents_summary": "; ".join([f"{doc.get('type')}:{doc.get('number') or 'N/A'}" for doc in d.get("documents", [])])
                })

        mem = io.StringIO()
        writer = csv.DictWriter(mem, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            writer.writerow({h: r.get(h, "") for h in headers})
        mem.seek(0)

        filename = f"export_{t}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.csv"
        return send_file(io.BytesIO(mem.getvalue().encode("utf-8")), mimetype="text/csv",
                         as_attachment=True, download_name=filename)
    except Exception as e:
        print("❌ /export_csv error:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# -----------------------
# simple health endpoint
# -----------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()}), 200

# -----------------------
# run
# -----------------------
if __name__ == "__main__":
    print("Starting KycVault backend on http://127.0.0.1:5000")
    app.run(debug=True)
