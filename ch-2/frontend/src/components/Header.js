import React, { useState } from 'react';
import { 
  IconButton, 
  FormControl, 
  Select, 
  MenuItem, 
  Badge,
  Tooltip,
  Fade,
  Button,
  Chip
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import SmartToyIcon from '@mui/icons-material/SmartToy'; // For OpenAI icon
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome'; // For Gemini icon
import ScienceIcon from '@mui/icons-material/Science'; // For Claude icon
import PhotoLibraryIcon from '@mui/icons-material/PhotoLibrary';
import SettingsIcon from '@mui/icons-material/Settings';
import BiotechIcon from '@mui/icons-material/Biotech';
import SpeedIcon from '@mui/icons-material/Speed';
import { useTheme } from '../context/ThemeContext';
import './Header.css';

function Header({ toggleSidebar, selectedModel, onModelChange }) {
  const { theme } = useTheme();
  const [lastChanged, setLastChanged] = useState(0);
  // New state for tracking API usage
  const [apiUsage, setApiUsage] = useState(67); // Example usage percentage
  
  // Add debugging to confirm model selection changes
  const handleModelChange = (event) => {
    const newModel = event.target.value;
    setLastChanged(Date.now());
    console.log(`%c🔄 Model selection changed to: ${newModel}`, 
      'background-color: #4b0082; color: white; padding: 2px 6px; border-radius: 4px;');
    onModelChange(newModel);
  };

  // Simulate API quota usage (in a real app, fetch this from backend)
  React.useEffect(() => {
    const interval = setInterval(() => {
      setApiUsage(prev => {
        const newValue = prev + Math.random() * 2 - 0.5;
        return Math.min(Math.max(newValue, 0), 100);
      });
    }, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  // Helper to determine if a model has image capabilities
  const hasImageCapabilities = (model) => {
    return ['gemini', 'claude'].includes(model);
  };
  
  return (
    <div className={`chat-header glassmorphism ${theme}-theme`}>
      <div className="header-left">
        <IconButton
          className="header-icon-button"
          onClick={toggleSidebar}
          aria-label="Toggle sidebar"
          size="medium"
        >
          <MenuIcon />
        </IconButton>
        
        <h1 className="header-title">AI Assistant</h1>
        
        <div className="header-version-badge">
          <span>v1.3</span>
        </div>
      </div>
      
      <div className="header-center">
        <div className={`model-selector-container ${selectedModel}-model`}>
          <Badge 
            color={
              selectedModel === 'gemini' ? 'primary' : 
              selectedModel === 'claude' ? 'warning' : 'success'
            } 
            variant="dot"
            invisible={Date.now() - lastChanged > 5000}
          >
            <FormControl variant="outlined" size="small">
              <Select
                id="model-select"
                value={selectedModel || 'openai'}
                onChange={handleModelChange}
                className="model-select"
                displayEmpty
                MenuProps={{
                  PaperProps: {
                    sx: {
                      bgcolor: theme === 'dark' ? '#2d2d2d' : '#ffffff',
                      color: theme === 'dark' ? '#ffffff' : '#333333',
                      '& .MuiMenuItem-root': {
                        color: theme === 'dark' ? '#ffffff !important' : '#333333 !important',
                      },
                      '& .MuiMenuItem-root:hover': {
                        backgroundColor: theme === 'dark' ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.04)',
                      }
                    },
                    className: `${theme}-theme`
                  }
                }}
                renderValue={(selected) => (
                  <div className="model-select-value">
                    {selected === 'openai' ? (
                      <>
                        <SmartToyIcon fontSize="small" /> 
                        <span>ChatGPT</span>
                      </>
                    ) : selected === 'claude' ? (
                      <>
                        <ScienceIcon fontSize="small" /> 
                        <span>Claude</span>
                      </>
                    ) : (
                      <>
                        <AutoAwesomeIcon fontSize="small" /> 
                        <span>Gemini</span>
                      </>
                    )}
                  </div>
                )}
              >
                <MenuItem value="openai" className="model-menu-item">
                  <SmartToyIcon fontSize="small" className="model-icon" />
                  <span className="model-menu-text">ChatGPT</span>
                </MenuItem>
                <MenuItem value="gemini" className="model-menu-item">
                  <AutoAwesomeIcon fontSize="small" className="model-icon" />
                  <span className="model-menu-text">Gemini</span>
                </MenuItem>
                <MenuItem value="claude" className="model-menu-item">
                  <ScienceIcon fontSize="small" className="model-icon" />
                  <span className="model-menu-text">Claude</span>
                </MenuItem>
              </Select>
            </FormControl>
          </Badge>
        </div>
      
        {hasImageCapabilities(selectedModel) && (
          <Tooltip 
            title={`${selectedModel === 'claude' ? 'Claude' : 'Gemini'} can process images! Try uploading an image.`}
            placement="bottom"
            TransitionComponent={Fade}
            TransitionProps={{ timeout: 600 }}
          >
            <div className="feature-badge">
              <PhotoLibraryIcon fontSize="small" />
              <span className="badge-text">Images</span>
            </div>
          </Tooltip>
        )}
      </div>
    </div>
  );
}

export default Header;
