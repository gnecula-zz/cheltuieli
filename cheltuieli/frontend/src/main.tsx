import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { getAppBasename } from "./lib/base";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter basename={getAppBasename()}>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
