import React from "react";
import { useNavigate } from "react-router-dom";
import "./App.css"; 

const SignIn = () => {
  const navigate = useNavigate();

  const handleSignIn = (e) => {
    e.preventDefault();
    navigate("/home2"); 
  };

  return (
    <div className="form-page">
      <h2>Sign In</h2>
      <form onSubmit={handleSignIn}>
        <input type="text" placeholder="Name" required />
        <input type="email" placeholder="Email" required />
        <input type="password" placeholder="Password" required />

        <button type="submit" className="btn primary">Sign In</button>
      </form>
    </div>
  );
};

export default SignIn;
