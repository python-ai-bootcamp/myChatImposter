import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';

import HomePage from './pages/HomePage';
import EditPage from './pages/EditPage';
import LinkPage from './pages/LinkPage';
import GroupTrackingPage from './pages/GroupTrackingPage';

function App() {
  return (
    <Router>
      <div>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/edit/:userId" element={<EditPage />} />
          <Route path="/link/:userId" element={<LinkPage />} />
          <Route path="/tracking/:userId" element={<GroupTrackingPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
