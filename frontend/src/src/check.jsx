import React, { useState } from "react";
import axios from "axios";
import "./App.css";
import { FiLogOut } from "react-icons/fi";

const Check = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e) => setSelectedFile(e.target.files[0]);

  const handleUpload = async () => {
    if (!selectedFile) return alert("⚠️ Please select an image!");

    setLoading(true);

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("userName", localStorage.getItem("userName"));
    formData.append("userDob", localStorage.getItem("userDob"));
    formData.append("userGender", localStorage.getItem("userGender"));

    try {
      const response = await axios.post("http://127.0.0.1:5000/upload", formData);
      setResult(response.data);
    } catch (error) {
      console.error(error);
      alert("❌ Upload failed!");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    alert("👋 Logged out!");
    window.location.href = "/login";
  };

  const RiskBadge = ({ level }) => {
    const style = {
      Low: { background: "#4CAF50", color: "white" },
      Medium: { background: "#FFB300", color: "black" },
      High: { background: "#E53935", color: "white" }
    };

    return (
      <span
        style={{
          padding: "6px 14px",
          borderRadius: "6px",
          fontWeight: "bold",
          display: "inline-block",
          marginTop: "8px",
          ...style[level]
        }}
      >
        {level} Risk
      </span>
    );
  };

  const renderRecord = (item) => (
    <div className="record-item">
      <h4>{item["Document Type"]}</h4>

      {item["Document Type"] === "Aadhaar" && (
        <>
          <p><b>Name:</b> {item.Name}</p>
          <p><b>DOB:</b> {item.DOB}</p>
          <p><b>Gender:</b> {item.Gender}</p>
          <p><b>Aadhaar Number:</b> {item["Aadhaar Number"]}</p>
        </>
      )}

      {item["Document Type"] === "PAN" && (
        <>
          <p><b>Name:</b> {item.Name}</p>
          <p><b>Father’s Name:</b> {item["Father's Name"]}</p>
          <p><b>PAN Number:</b> {item["PAN Number"]}</p>
        </>
      )}

      {item["Document Type"] === "Driving License" && (
        <>
          <p><b>Name:</b> {item.Name}</p>
          <p><b>DOB:</b> {item.DOB}</p>
          <p><b>DL Number:</b> {item["DL Number"]}</p>
          <p><b>Valid Till:</b> {item["Valid Till"]}</p>
        </>
      )}
    </div>
  );

  return (
    <div className="check-page">

      <div className="logout-icon" onClick={handleLogout}>
        <FiLogOut size={28} title="Logout" />
      </div>

      <h1>🧠 KYC Document Verification</h1>
      <p>Upload Aadhaar, PAN or Driving License for extraction</p>

      <div className="upload-section">
        <input type="file" onChange={handleFileChange} />
        <button onClick={handleUpload} disabled={loading}>
          {loading ? "Processing..." : "Upload & Extract"}
        </button>
      </div>

      {result && (
        <div className="result-box">
          <h2>✅ Extracted Details</h2>
          {renderRecord(result)}

          <p><b>Fraud Score:</b> {result.fraudScore}%</p>
          <RiskBadge level={result.riskLevel} />

          {result.Reasons?.length > 0 && (
            <div style={{ marginTop: "12px" }}>
              <b>Reasons:</b>
              <ul>
                {result.Reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Check;
