import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';

import HomePage from './pages/HomePage';
import EditPage from './pages/EditPage';
import LinkPage from './pages/LinkPage';

function App() {
  return (
    <Router>
      <div>
        <h1>WhatsApp Imposter Control Panel</h1>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/edit/:filename" element={<EditPage />} />
          <Route path="/link/:filename" element={<LinkPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
