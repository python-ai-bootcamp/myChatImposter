import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';

import HomePage from './pages/HomePage';
import EditPage from './pages/EditPage';
import LinkPage from './pages/LinkPage';

function App() {
  return (
    <Router>
      <div>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/edit/:userId" element={<EditPage />} />
          <Route path="/link/:userId" element={<LinkPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
