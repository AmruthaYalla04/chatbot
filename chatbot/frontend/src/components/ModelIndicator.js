import React from 'react';
import { Chip, Tooltip } from '@mui/material';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import '../Chat.css';

/**
 * A component to display which AI model is being used
 */
const ModelIndicator = ({ selectedModel, loading }) => {
  // Determine icon and color based on the selected model
  const getModelInfo = (model) => {
    const modelName = model ? model.toLowerCase() : 'openai';
    
    if (modelName === 'gemini') {
      return {
        icon: <AutoAwesomeIcon fontSize="small" style={{ marginRight: '4px' }} />,
        label: 'Gemini',
        color: '#1a73e8', // Google blue
        backgroundColor: '#e8f0fe' // Light blue background
      };
    } else {
      return {
        icon: <SmartToyIcon fontSize="small" style={{ marginRight: '4px' }} />,
        label: 'ChatGPT',
        color: '#10a37f', // OpenAI green
        backgroundColor: '#e6f6f2' // Light green background
      };
    }
  };

  const { icon, label, color, backgroundColor } = getModelInfo(selectedModel);

  return (
    <Tooltip title={`Currently using ${label} AI model`} arrow placement="bottom">
      <Chip
        icon={icon}
        label={loading ? `${label} thinking...` : label}
        style={{
          color: color,
          backgroundColor: backgroundColor,
          border: `1px solid ${color}`,
          fontWeight: 'bold',
          opacity: loading ? 0.7 : 1
        }}
        size="small"
        className={`model-indicator ${loading ? 'model-loading' : ''}`}
      />
    </Tooltip>
  );
};

export default ModelIndicator;
