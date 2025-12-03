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

  const fetchData = () => {
    axios.get("http://127.0.0.1:5000/all-records")
      .then((res) => setRecords(res.data))
      .catch((err) => console.log(err));
  };

  useEffect(() => { fetchData(); }, []);

  // risk stats
  const low = records.filter((r) => r.overallRiskLevel === "Low").length;
  const medium = records.filter((r) => r.overallRiskLevel === "Medium").length;
  const high = records.filter((r) => r.overallRiskLevel === "High").length;

  const verified = low;
  const fraud = medium + high;

  const handleLogout = () => {
    localStorage.removeItem("isAdmin");
    window.location.href = "/admin-login";
  };

  const exportCSV = (type) => {
    window.location.href = `http://127.0.0.1:5000/export_csv?type=${type}`;
  };

  return (
    <div className="dashboard-container">

      <button onClick={handleLogout}
        style={{
          position: "absolute", top: "30px", right: "40px",
          background: "#E53935", padding: "8px 14px",
          borderRadius: "6px", color: "white", border: "none",
          cursor: "pointer", fontWeight: "bold"
        }}>
        Logout
      </button>

      <button
        onClick={() => (window.location.href = "/alerts")}
        className="alerts-btn"
        style={{
          position: "absolute", top: "90px", right: "40px",
          background: "#f59e0b", padding: "8px 14px",
          borderRadius: "6px", border: "none", cursor: "pointer"
        }}>
        🚨 Fraud Alerts
      </button>

      {/* CSV EXPORT BUTTONS */}
      <div style={{ marginTop: "20px" }}>
        <button onClick={() => exportCSV("all")} className="csv-btn">⬇ Export All</button>
        <button onClick={() => exportCSV("approved")} className="csv-btn">⬇ Export Approved</button>
        <button onClick={() => exportCSV("rejected")} className="csv-btn">⬇ Export Rejected</button>
        <button onClick={() => exportCSV("alerts")} className="csv-btn">⬇ Export AML Alerts</button>
      </div>

      <h1 className="title">📊 Fraud Detection Dashboard</h1>

      <div className="charts-container">
        <div className="chart-box">
          <h3>Verified vs Fraud Documents</h3>
          <Pie data={{
            labels: ["Verified", "Fraud / Suspicious"],
            datasets: [{ data: [verified, fraud], backgroundColor: ["#4CAF50", "#E53935"] }]
          }} />
        </div>

        <div className="chart-box">
          <h3>Fraud Risk Distribution</h3>
          <Bar data={{
            labels: ["Low", "Medium", "High"],
            datasets: [{
              label: "Count",
              data: [low, medium, high],
              backgroundColor: ["#4CAF50", "#FFB300", "#E53935"]
            }]
          }} />
        </div>
      </div>

      <h2 className="table-title">📂 Recent Verifications</h2>
      <table className="records-table">
        <thead>
          <tr>
            <th>User</th>
            <th>Documents</th>
            <th>Fraud Score</th>
            <th>Risk</th>
            <th>Final Status</th>
          </tr>
        </thead>

        <tbody>
          {records.slice(-5).reverse().map((r, i) => (
            <tr key={i}>
              <td>{r.userName}</td>
              <td>{r.documents?.map(d => d.type).join(", ")}</td>
              <td>{r.overallFraudScore}%</td>
              <td style={{ color: r.overallRiskLevel === "High" ? "red" : r.overallRiskLevel === "Medium" ? "orange" : "lightgreen" }}>{r.overallRiskLevel}</td>
              <td>{r.finalStatus}</td>
            </tr>
          ))}
        </tbody>
      </table>

    </div>
  );
};

export default Dashboard;
