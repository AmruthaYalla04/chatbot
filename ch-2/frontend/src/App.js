import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { ThemeProvider } from './context/ThemeContext';
import { AppSettingsProvider } from './context/AppSettingsContext';
import Login from './Login';
import Chat from './Chat';
import './App.css';

// Access Google Client ID from environment variables with fallback
const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID || "748513885856-a8upflc11lkknnnqrrscdcnhije274cr.apps.googleusercontent.com";

// Check if we have a valid client ID
console.log(`[App] Initializing with Google Client ID: ${GOOGLE_CLIENT_ID ? 'Present' : 'MISSING'}`);

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    return !!localStorage.getItem('access_token');
  });

  useEffect(() => {
    const checkAuthAndRedirect = () => {
      const token = localStorage.getItem('access_token');
      const currentPath = window.location.pathname;

      if (token) {
        setIsAuthenticated(true);
        if (currentPath === '/login') {
          window.location.href = '/chat';
        }
      } else {
        setIsAuthenticated(false);
        if (currentPath !== '/login') {
          window.location.href = '/login';
        }
      }
    };

    checkAuthAndRedirect();
    window.addEventListener('storage', checkAuthAndRedirect);
    return () => window.removeEventListener('storage', checkAuthAndRedirect);
  }, []);

  return (
    <ThemeProvider>
      <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
        <AppSettingsProvider>
          <Router>
            <Routes>
              {/* Root route - redirect to login if not authenticated */}
              <Route 
                path="/" 
                element={
                  isAuthenticated ? (
                    <Navigate to="/chat" replace />
                  ) : (
                    <Navigate to="/login" replace />
                  )
                } 
              />

              {/* Login route */}
              <Route 
                path="/login" 
                element={
                  isAuthenticated ? (
                    <Navigate to="/chat" replace />
                  ) : (
                    <Login setIsAuthenticated={setIsAuthenticated} />
                  )
                } 
              />

              {/* Chat route - protected */}
              <Route 
                path="/chat" 
                element={
                  isAuthenticated ? (
                    <Chat />
                  ) : (
                    <Navigate to="/login" replace />
                  )
                } 
              />
            </Routes>
          </Router>
        </AppSettingsProvider>
      </GoogleOAuthProvider>
    </ThemeProvider>
  );
}

export default App;
