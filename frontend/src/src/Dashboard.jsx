import React, { useEffect, useState } from "react";
import axios from "axios";
import { Pie, Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  ArcElement,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend
} from "chart.js";
import "./Dashboard.css";

ChartJS.register(ArcElement, BarElement, CategoryScale, LinearScale, Tooltip, Legend);

const Dashboard = () => {
  const [records, setRecords] = useState([]);

  useEffect(() => {
    axios.get("http://127.0.0.1:5000/records")
      .then(res => setRecords(res.data))
      .catch(err => console.log(err));
  }, []);

  const low = records.filter(r => r.riskLevel === "Low").length;
  const medium = records.filter(r => r.riskLevel === "Medium").length;
  const high = records.filter(r => r.riskLevel === "High").length;

  const verified = low;
  const fraud = medium + high;

  const handleLogout = () => {
    localStorage.removeItem("isAdmin");
    window.location.href = "/admin-login";
  };

  return (
    <div className="dashboard-container">

      {/* Logout Button */}
      <button
        onClick={handleLogout}
        style={{
          position: "absolute",
          top: "30px",
          right: "40px",
          background: "#E53935",
          padding: "8px 14px",
          borderRadius: "6px",
          color: "white",
          border: "none",
          cursor: "pointer",
          fontWeight: "bold"
        }}
      >
        Logout
      </button>

      <h1 className="title">📊 Fraud Detection Dashboard</h1>

      <div className="charts-container">
        <div className="chart-box">
          <h3>Verified vs Fraud Documents</h3>
          <Pie
            data={{
              labels: ["Verified", "Fraud / Suspicious"],
              datasets: [{
                data: [verified, fraud],
                backgroundColor: ["#4CAF50", "#E53935"]
              }]
            }}
          />
        </div>

        <div className="chart-box">
          <h3>Fraud Risk Distribution</h3>
          <Bar
            data={{
              labels: ["Low", "Medium", "High"],
              datasets: [{
                label: "Count",
                data: [low, medium, high],
                backgroundColor: ["#4CAF50", "#FFB300", "#E53935"]
              }]
            }}
          />
        </div>
      </div>

      <h2 className="table-title">📂 Recent Documents</h2>
      <table className="records-table">
        <thead>
          <tr>
            <th>Document Type</th>
            <th>Name</th>
            <th>Fraud Score</th>
            <th>Risk Level</th>
          </tr>
        </thead>
        <tbody>
          {records.slice(-5).reverse().map((r, i) => (
            <tr key={i}>
              <td>{r["Document Type"]}</td>
              <td>{r.Name}</td>
              <td>{r.fraudScore}%</td>
              <td style={{ color:
                r.riskLevel === "High" ? "red" :
                r.riskLevel === "Medium" ? "orange" : "lightgreen"
              }}>
                {r.riskLevel}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

    </div>
  );
};

export default Dashboard;
