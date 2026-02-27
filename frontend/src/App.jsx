import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import PrivateRoute from './components/PrivateRoute'
import Layout from './components/Layout'
import Login from './pages/Login'
import Signup from './pages/Signup'
import ForgotPassword from './pages/ForgotPassword'
import Dashboard from './pages/Dashboard'
import Recordings from './pages/Recordings'
import RecordingDetail from './pages/RecordingDetail'
import Sellers from './pages/Sellers'
import SellerForm from './pages/SellerForm'
import Account from './pages/Account'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />

          <Route path="/dashboard" element={<PrivateRoute><Layout><Dashboard /></Layout></PrivateRoute>} />
          <Route path="/recordings" element={<PrivateRoute><Layout><Recordings /></Layout></PrivateRoute>} />
          <Route path="/recordings/:id" element={<PrivateRoute><Layout><RecordingDetail /></Layout></PrivateRoute>} />
          <Route path="/sellers" element={<PrivateRoute><Layout><Sellers /></Layout></PrivateRoute>} />
          <Route path="/sellers/new" element={<PrivateRoute><Layout><SellerForm /></Layout></PrivateRoute>} />
          <Route path="/sellers/:id" element={<PrivateRoute><Layout><SellerForm /></Layout></PrivateRoute>} />
          <Route path="/account" element={<PrivateRoute><Layout><Account /></Layout></PrivateRoute>} />

          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
