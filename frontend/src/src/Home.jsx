import React from "react";
import { useNavigate } from "react-router-dom";
import "./App.css";

const Home = () => {
  const navigate = useNavigate();

  return (
    <div className="hero">
      <button className="badge">🚀 AI Powered KYC Detection</button>
      <h1>Detect Identity Verification in Seconds</h1>
      <p>Verify the authenticity of KYC with AI-powered analysis.</p>

      <div className="btn-group">
        <button className="btn primary" onClick={() => navigate("/login")}>
          Get Started
        </button>
        <button className="btn secondary">Learn More</button>
      </div>
    </div>
  );
};

export default Home;
