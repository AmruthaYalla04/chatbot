import React, { createContext, useState, useContext, useEffect } from 'react';

// Create context
export const AppSettingsContext = createContext();

// Provider component
export const AppSettingsProvider = ({ children }) => {
  // Settings with default values
  const [settings, setSettings] = useState({
    // AI Model settings
    defaultModel: 'openai',
    temperature: 0.7,
    maxTokens: 1000,
    
    // UI settings
    showTimestamps: true,
    compactMode: false,
    codeHighlighting: true,
    
    // Behavior settings
    autoSuggest: true,
    saveHistory: true,
    apiRateLimit: 100,
    
    // Theme settings (still handled by ThemeContext)
    theme: localStorage.getItem('theme') || 'light',
  });

  // Load settings from localStorage on initial load
  useEffect(() => {
    try {
      const savedSettings = localStorage.getItem('app_settings');
      if (savedSettings) {
        setSettings(prev => ({
          ...prev,
          ...JSON.parse(savedSettings)
        }));
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
  }, []);

  // Save settings to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem('app_settings', JSON.stringify(settings));
    } catch (error) {
      console.error('Failed to save settings:', error);
    }
  }, [settings]);

  // Function to update a single setting
  const updateSetting = (key, value) => {
    setSettings(prev => ({
      ...prev,
      [key]: value
    }));
  };

  return (
    <AppSettingsContext.Provider value={{ settings, updateSetting, setSettings }}>
      {children}
    </AppSettingsContext.Provider>
  );
};

// Custom hook for using the settings
export const useAppSettings = () => {
  const context = useContext(AppSettingsContext);
  if (context === undefined) {
    throw new Error('useAppSettings must be used within an AppSettingsProvider');
  }
  return context;
};
