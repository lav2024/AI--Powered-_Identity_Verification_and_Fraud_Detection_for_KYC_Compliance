import React from "react";
import { useNavigate } from "react-router-dom";
import "./Home2.css"; 

const Home2 = () => {
  const navigate = useNavigate(); 

  return (
    <div className="home2-wrapper">
      <div className="home2-inner">
        <section className="hero2">
          <h1>KYC Detection that Made Easy</h1>

          {/* ✅ Navigate to user details page before checking */}
          <button className="btn check-now" onClick={() => navigate("/user-details")}>
            Check Now
          </button>

          <button className="btn check-now" onClick={() => navigate("/dashboard")} style={{ marginLeft: "15px" }}>
            View Dashboard
          </button>
          
        </section>

        <section className="about2">
          <h2>About Us</h2>
          <p>
            AI-powered identity verification and fraud detection system for
            KYC/AML compliance in the BFSI sector — verify AADHAR-based
            addresses, and detect fraudulent documents efficiently and
            accurately.
          </p>
        </section>
      </div>

      <footer className="footer2">
        <p>&copy; 2026 KycVault. All rights reserved.</p>
        <ul>
          <li><button className="footer-link">Terms & Conditions</button></li>
          <li><button className="footer-link">Privacy Policy</button></li>
          <li><button className="footer-link">Contact Us</button></li>
        </ul>
      </footer>

    </div>
  );
};

export default Home2;
