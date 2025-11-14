import React from "react";
import { useNavigate } from "react-router-dom";
import "./App.css"; // optional if styling is global

const Login = () => {
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();
    navigate("/home2"); // redirects to Home2 after login
  };

  return (
    <div className="form-page">
      <h2>Login</h2>
      <form onSubmit={handleLogin}>
        <input type="text" placeholder="Username" required />
        <input type="password" placeholder="Password" required />

        <div className="remember-forgot">
          <label>
            <input type="checkbox" /> Remember me
          </label>
          <button className="link-button">Forgot Password?</button>
        </div>

        <button type="submit" className="btn primary">Login</button>

        <p>
          Don’t have an account?{" "}
          <a href="/signin" className="link">Register</a>
        </p>
      </form>
    </div>
  );
};

export default Login;
