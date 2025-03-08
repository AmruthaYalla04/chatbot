import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { IconButton, LinearProgress, Tooltip } from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import PhotoIcon from '@mui/icons-material/Photo';
import '../Chat.css';

const Message = ({ message, onEditMessage, selectedModel }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(message.content);
  const [imageLoading, setImageLoading] = useState(false);
  const [imageError, setImageError] = useState(false);
  
  // Check if the message contains an image
  const hasImage = message.content.includes('![') && 
                 (message.content.includes('](image://') ||
                  message.content.includes('](data:image') ||
                  message.content.includes('](http'));

  useEffect(() => {
    // Reset image states when message changes
    if (hasImage) {
      setImageLoading(true);
      setImageError(false);
    }
  }, [message.id, hasImage]);

  const handleEditClick = () => {
    setIsEditing(true);
    setEditContent(message.content);
  };

  const handleSaveClick = () => {
    onEditMessage(message.id, editContent);
    setIsEditing(false);
  };

  const handleCancelClick = () => {
    setIsEditing(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      handleSaveClick();
    } else if (e.key === 'Escape') {
      handleCancelClick();
    }
  };

  // Custom renderer for images that handles our special image:// protocol
  const ImageRenderer = ({ src, alt }) => {
    // Check if it's our special protocol for temporarily stored images
    const [actualSrc, setActualSrc] = useState(src);
    
    useEffect(() => {
      if (src.startsWith('image://')) {
        const imageId = src.replace('image://', '');
        const base64Data = sessionStorage.getItem(imageId);
        
        if (base64Data) {
          setActualSrc(`data:image/jpeg;base64,${base64Data}`);
        } else {
          console.error(`Image data not found for ${imageId}`);
          setImageError(true);
        }
      }
    }, [src]);
    
    return (
      <div className="message-image-container">
        {imageLoading && <LinearProgress className="image-loading-progress" />}
        {imageError && (
          <div className="image-error">
            <PhotoIcon />
            <span>Failed to load image</span>
          </div>
        )}
        <img
          src={actualSrc}
          alt={alt || "Generated image"}
          className="message-image"
          onLoad={() => setImageLoading(false)}
          onError={() => {
            setImageLoading(false);
            setImageError(true);
          }}
          style={{ display: imageError ? 'none' : 'block' }}
        />
      </div>
    );
  };

  // Update the getModelInfo function to include Claude
  const getModelInfo = () => {
    // Always use the message's model if available, fallback to selected model
    const modelName = message.model || selectedModel;
    
    if (!modelName) return { label: '', icon: null };
    
    const modelLower = modelName.toLowerCase();
    
    if (modelLower.includes('gemini')) {
      return { 
        label: 'Gemini', 
        color: '#1a73e8', // Google blue
        className: 'gemini'
      };
    } else if (modelLower.includes('claude')) {
      return { 
        label: 'Claude', 
        color: '#9e4f63', // Claude burgundy 
        className: 'claude'
      };
    } else {
      return { 
        label: 'ChatGPT', 
        color: '#10a37f', // OpenAI green
        className: 'openai'
      };
    }
  };

  const { label, color, className } = getModelInfo();

  return (
    <li className={`message ${message.role} ${hasImage ? 'has-image' : ''}`}>
      {isEditing ? (
        <div className="edit-message-container">
          <textarea
            className="edit-message-input"
            value={editContent}
            onChange={(e) => setEditContent(e.target.value)}
            onKeyDown={handleKeyDown}
            autoFocus
          />
          <div className="edit-message-actions">
            <button className="save-edit-button" onClick={handleSaveClick}>
              <i className="fas fa-check"></i>
            </button>
            <button className="cancel-edit-button" onClick={handleCancelClick}>
              <i className="fas fa-times"></i>
            </button>
          </div>
        </div>
      ) : (
        <div className="message-content">
          <div className="markdown-content">
            <ReactMarkdown
              components={{
                img: ImageRenderer
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
          
          {message.role === 'user' && (
            <IconButton 
              className="edit-message-button" 
              onClick={handleEditClick}
              size="small"
            >
              <EditIcon fontSize="small" />
            </IconButton>
          )}
          
          {/* Show model info for assistant messages */}
          {message.role === 'assistant' && (
            <Tooltip title={`Generated by ${label}`}>
              <div 
                className={`model-indicator ${className}`}
                style={{ backgroundColor: `${color}22`, color: color }}
              >
                {label}
                {hasImage && " • Image"}
              </div>
            </Tooltip>
          )}
        </div>
      )}
    </li>
  );
};

export default Message;
