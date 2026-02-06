import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';

import HomePage from './pages/HomePage';
import EditPage from './pages/EditPage';
import LoginPage from './pages/LoginPage';
import RestrictedEditPage from './pages/RestrictedEditPage';


function App() {
  return (
    <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <div>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/admin/home" element={<HomePage enableFiltering={true} showOwnerColumn={true} />} />
          <Route path="/user/home" element={<HomePage enableFiltering={false} showOwnerColumn={false} />} />
          <Route path="/admin/edit/:botId" element={<EditPage />} />
          <Route path="/user/edit/:botId" element={<RestrictedEditPage />} />
          {/* Default Route - Redirect logic will be handled in HomePage or a root component, but for now we map root to HomePage to handle redirection logic there */}
          <Route path="/" element={<HomePage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
