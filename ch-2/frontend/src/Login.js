import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google';
import { useTheme } from './context/ThemeContext';
import ThemeToggle from './components/ThemeToggle';
import './Login.css';

// Access Google Client ID from environment variables
const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID || "748513885856-a8upflc11lkknnnqrrscdcnhije274cr.apps.googleusercontent.com"; // Fallback for development

function Login({ setIsAuthenticated }) {
  const { theme } = useTheme();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  // Clear any existing auth data when login component mounts
  useEffect(() => {
    localStorage.clear();
    setIsAuthenticated(false);
  }, [setIsAuthenticated]);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      navigate('/');
      return;
    }
  }, [navigate]);

  const handleGoogleLoginSuccess = async (response) => {
    setLoading(true);
    setError(null);
    
    console.log("Google login response received, credential length:", response.credential?.length);
    
    try {
      console.log("Sending request to backend...");
      const res = await axios.post('http://localhost:8000/google-login', {
        token: response.credential
      });
      
      console.log("Login response:", res.status);
      
      if (res.data.access_token) {
        // Store user data in localStorage
        const userData = {
          'access_token': res.data.access_token,
          'user_id': res.data.user_id.toString(),
          'profile_image': res.data.profile_image || '',
          'display_name': res.data.display_name || '',
          'username': res.data.username || '',
          'email': res.data.email || '',
          'login_method': 'google'
        };

        // Store all data at once
        Object.entries(userData).forEach(([key, value]) => {
          localStorage.setItem(key, value);
        });
        
        // Update auth state and redirect
        setIsAuthenticated(true);
        
        console.log("Authentication successful, redirecting to /chat");
        // Force a hard redirect to /chat
        window.location.href = '/chat';
      } else {
        throw new Error('Invalid response from server');
      }
    } catch (error) {
      console.error('Google login error:', error);
      let errorMessage = 'Login failed. Please try again.';
      
      // Extract more specific error message if available
      if (error.response && error.response.data) {
        errorMessage = `Login failed: ${error.response.data.detail || 'Unknown error'}`;
        console.error('Error details:', error.response.data);
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLoginFailure = (error) => {
    console.error('Google login failed', error);
    setError('Google login failed. Please try again.');
  };

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <div className={`login-container ${theme}-theme`}>
        <div className="theme-toggle-wrapper" style={{
          position: 'absolute',
          top: '20px',
          right: '20px',
          zIndex: 100,
          background: 'rgba(255,255,255,0.2)',
          padding: '8px 12px',
          borderRadius: '20px',
          backdropFilter: 'blur(5px)'
        }}>
          <ThemeToggle />
        </div>
        
        <div className="login-box">
          <h1>Welcome to ChatBot</h1>
          
          {error && <div className="error-message">{error}</div>}
          
          <div className="google-login">
            <GoogleLogin
              onSuccess={handleGoogleLoginSuccess}
              onError={handleGoogleLoginFailure}
              disabled={loading}
              useOneTap
              text="signin_with"
              shape="rectangular"
              width="100%"
              size="large"
              logo_alignment="center"
              theme={theme === 'dark' ? 'filled_black' : 'outline'}
            />
          </div>
          
          {loading && <div className="loading-message">Logging in</div>}
        </div>
      </div>
    </GoogleOAuthProvider>
  );
}

export default Login;
