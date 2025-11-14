import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./UserDetails.css";

const UserDetails = () => {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [dob, setDob] = useState("");
  const [gender, setGender] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!name || !dob || !gender) {
      return alert("⚠️ Please fill all fields.");
    }

    // Save details for fraud detection later
    localStorage.setItem("userName", name);
    localStorage.setItem("userDob", dob);
    localStorage.setItem("userGender", gender);

    navigate("/check"); // go to upload page
  };

  return (
    <div className="user-details-container">
      <h2>🔐 Identity Verification</h2>
      <p>Please enter your details for document matching</p>

      <form onSubmit={handleSubmit} className="details-form">
        <label>Name (as per ID):</label>
        <input
          type="text"
          placeholder="Full legal name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />

        <label>Date of Birth:</label>
        <input
          type="date"
          value={dob}
          onChange={(e) => setDob(e.target.value)}
        />

        <label>Gender:</label>
        <select value={gender} onChange={(e) => setGender(e.target.value)}>
          <option value="">Select Gender</option>
          <option value="Male">Male</option>
          <option value="Female">Female</option>
        </select>

        <button type="submit">Next →</button>
      </form>
    </div>
  );
};

export default UserDetails;
