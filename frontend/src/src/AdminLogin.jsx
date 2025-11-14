import React, { useState } from "react";
import "./App.css";

const AdminLogin = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleLogin = (e) => {
    e.preventDefault();

    if (username === "Lav" && password === "Lav123") {
      localStorage.setItem("isAdmin", "true");
      alert("✅ Login Successful");
      window.location.href = "/dashboard";
    } else {
      alert("❌ Invalid Username or Password");
    }
  };

  return (
    <div className="login-container">
      <h2>🔐 Admin Login</h2>

      <form onSubmit={handleLogin} className="login-form">
        <input
          type="text"
          placeholder="Admin Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />

        <input
          type="password"
          placeholder="Admin Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <button type="submit">Login</button>
      </form>
    </div>
  );
};

export default AdminLogin;
