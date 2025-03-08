import React from 'react';
import { useTheme } from '../context/ThemeContext';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import LightModeIcon from '@mui/icons-material/LightMode';
import './ThemeToggle.css';

const ThemeToggle = () => {
  const { theme, toggleTheme } = useTheme();
  
  return (
    <div className="theme-toggle-container">
      <div className="theme-icon">
        {theme === 'light' ? <LightModeIcon /> : <DarkModeIcon />}
      </div>
      <label className="theme-toggle">
        <input 
          type="checkbox" 
          checked={theme === 'dark'}
          onChange={toggleTheme}
        />
        <span className="theme-toggle-slider"></span>
      </label>
    </div>
  );
};

export default ThemeToggle;
