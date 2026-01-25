import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';

import HomePage from './pages/HomePage';
import EditPage from './pages/EditPage';


function App() {
  return (
    <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <div>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/edit/:userId" element={<EditPage />} />

        </Routes>
      </div>
    </Router>
  );
}

export default App;
