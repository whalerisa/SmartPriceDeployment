// src/main.jsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import { AuthProvider } from "./context/AuthContext.jsx";
import { QuoteProvider } from "./context/QuoteContext.jsx";
import "./style.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <BrowserRouter>
    <AuthProvider>
      <QuoteProvider>
        <App />
      </QuoteProvider>
    </AuthProvider>
  </BrowserRouter>
);
