import React from "react";
import { Routes, Route, Link, Navigate } from "react-router-dom";
import LiquidEther from "./LiquidEther";
import Home from "./Home";
import SignIn from "./SignIn";
import Login from "./Login";
import Home2 from "./Home2";
import Check from "./check";
import UserDetails from "./UserDetails";
import Dashboard from "./Dashboard";
import AdminLogin from "./AdminLogin";
import "./App.css";

function App() {
  const isAdmin = localStorage.getItem("isAdmin");

  return (
    <div className="App">
      <LiquidEther
        colors={["#5227FF", "#FF9FFC", "#B19EEF"]}
        mouseForce={20}
        cursorSize={100}
        isViscous={false}
        viscous={30}
        iterationsViscous={32}
        iterationsPoisson={32}
        resolution={0.5}
        isBounce={false}
        autoDemo={true}
        autoSpeed={0.5}
        autoIntensity={2.2}
        takeoverDuration={0.25}
        autoResumeDelay={3000}
        autoRampDuration={0.6}
      />

      <nav className="navbar">
        <div className="logo">🕵️‍♂️ KycVault</div>
        <div className="nav-links">
          <Link to="/">Home</Link>
          <Link to="/signin">Contact</Link>
          <Link to="/login">Info</Link>
          <Link to="/admin-login">Admin</Link>
        </div>
      </nav>

      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/signin" element={<SignIn />} />
        <Route path="/login" element={<Login />} />
        <Route path="/home2" element={<Home2 />} />
        <Route path="/user-details" element={<UserDetails />} />
        <Route path="/check" element={<Check />} />
        <Route path="/admin-login" element={<AdminLogin />} />

        {/* Protected Dashboard Route */}
        <Route
          path="/dashboard"
          element={isAdmin ? <Dashboard /> : <Navigate to="/admin-login" />}
        />
      </Routes>
    </div>
  );
}

export default App;
