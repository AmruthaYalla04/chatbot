import React, { useState } from 'react';
import { IconButton, Tooltip, Collapse } from '@mui/material';
import LogoutIcon from '@mui/icons-material/Logout';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import GoogleIcon from '@mui/icons-material/Google';
import ThemeToggle from './ThemeToggle';
import { useTheme } from '../context/ThemeContext';
import './SidebarFooter.css';

const SidebarFooter = ({ profileData, handleLogout }) => {
  const [expanded, setExpanded] = useState(false);
  const { theme } = useTheme();
  
  const toggleExpanded = () => setExpanded(!expanded);
  
  const firstLetter = profileData?.name?.charAt(0)?.toUpperCase() || 'U';
  const isGoogleLogin = profileData?.loginMethod === 'google';
  
  // Determine if we have a valid profile image
  const hasProfileImage = profileData?.image && profileData.image !== 'null' && profileData.image !== 'undefined';
  
return (
    <div className={`sidebar-footer ${theme === 'dark' ? 'dark' : 'light'}`}>
        <div 
            className={`sidebar-footer-collapsed ${expanded ? 'expanded' : ''}`}
            onClick={toggleExpanded}
        >
            <div className="user-avatar">
                {hasProfileImage ? (
                    <img 
                        src={profileData.image} 
                        alt={profileData.name} 
                        className="avatar-image" 
                        onError={(e) => {
                            e.target.onerror = null;
                            e.target.src = ''; // Fallback to letter avatar if image fails to load
                            e.target.style.display = 'none';
                            e.target.nextSibling.style.display = 'flex';
                        }}
                    />
                ) : null}
                <div className="avatar-letter" style={{display: hasProfileImage ? 'none' : 'flex'}}>
                    {firstLetter}
                </div>
            </div>
            
            <div className="user-info-compact">
                <span className="user-name">{profileData?.name || 'User'}</span>
                {isGoogleLogin && (
                    <span className="login-method">Google</span>
                )}
            </div>
            
            <IconButton 
                className="expand-button"
                aria-label={expanded ? "Collapse user panel" : "Expand user panel"}
            >
                {expanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
            </IconButton>
        </div>
        
        <Collapse in={expanded} timeout="auto" unmountOnExit>
            <div className="sidebar-footer-expanded">
                <div className="user-details">
                    {isGoogleLogin && (
                        <div className="google-login-badge">
                            <GoogleIcon fontSize="small" /> Google Account
                        </div>
                    )}
                    {profileData?.email && (
                        <div className="user-email">
                            {profileData.email}
                        </div>
                    )}
                </div>
                
                <div className="footer-actions">
                    <div className="theme-control">
                        <span className="action-label">Theme</span>
                        <ThemeToggle />
                    </div>
                    
                    <div className="account-actions">
                        <Tooltip title="Logout">
                            <IconButton 
                                onClick={handleLogout} 
                                className="action-button logout-button"
                            >
                                <LogoutIcon fontSize="small" />
                            </IconButton>
                        </Tooltip>
                    </div>
                </div>
            </div>
        </Collapse>
    </div>
);
};

export default SidebarFooter;
