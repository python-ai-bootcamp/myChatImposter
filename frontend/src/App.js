import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';

import HomePage from './pages/HomePage';
import EditPage from './pages/EditPage';
import LoginPage from './pages/LoginPage';
import RestrictedEditPage from './pages/RestrictedEditPage';


import GlobalHeader from './components/GlobalHeader';
import UserListPage from './pages/UserListPage';
import CreateUserPage from './pages/CreateUserPage';
import AdminUserEditPage from './pages/AdminUserEditPage';
import UserSelfEditPage from './pages/UserSelfEditPage';

import LandingPage from './pages/LandingPage';
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  return (
    <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <div>
        <GlobalHeader />
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />

          {/* Protected Routes */}
          <Route element={<ProtectedRoute />}>
            <Route path="/admin/dashboard" element={<HomePage enableFiltering={true} showOwnerColumn={true} />} />
            <Route path="/operator/dashboard" element={<HomePage enableFiltering={false} showOwnerColumn={false} />} />

            {/* Bot Edit Routes */}
            <Route path="/admin/edit/:botId" element={<EditPage />} />
            <Route path="/operator/bot/:botId" element={<RestrictedEditPage />} />

            {/* User Management Routes */}
            <Route path="/admin/users" element={<UserListPage />} />
            <Route path="/admin/users/create" element={<CreateUserPage />} />
            <Route path="/admin/users/edit/:userId" element={<AdminUserEditPage />} />
            <Route path="/operator/profile" element={<UserSelfEditPage />} />
          </Route>
        </Routes>
      </div>
    </Router>
  );
}

export default App;
