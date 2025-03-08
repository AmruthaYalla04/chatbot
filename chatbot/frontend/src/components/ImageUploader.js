import React, { useState } from 'react';
import { IconButton, CircularProgress, Snackbar, Alert, Tooltip, Badge } from '@mui/material';
import ImageIcon from '@mui/icons-material/Image';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import DescriptionIcon from '@mui/icons-material/Description';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import axios from 'axios';

const ImageUploader = ({ onResult, onError, disabled, selectedModel }) => {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(0);
  const [fileType, setFileType] = useState(null);
  
  // Function to compress image client-side if needed
  const compressImage = async (file) => {
    // Only compress if file is larger than 4MB
    if (file.size <= 4 * 1024 * 1024) return file;
    
    try {
      // Create image element
      const img = document.createElement('img');
      const reader = new FileReader();
      
      const loadImage = new Promise((resolve) => {
        reader.onload = (e) => {
          img.src = e.target.result;
          img.onload = () => resolve(img);
        };
        reader.readAsDataURL(file);
      });
      
      const image = await loadImage;
      
      // Calculate new dimensions (max 1024px)
      const maxDim = 1024;
      let width = image.width;
      let height = image.height;
      
      if (width > maxDim || height > maxDim) {
        if (width > height) {
          height = Math.round(height * (maxDim / width));
          width = maxDim;
        } else {
          width = Math.round(width * (maxDim / height));
          height = maxDim;
        }
      }
      
      // Create canvas
      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(image, 0, 0, width, height);
      
      // Convert to blob with quality reduction
      const blob = await new Promise(resolve => {
        canvas.toBlob(resolve, 'image/jpeg', 0.85);
      });
      
      // Convert blob to file
      return new File([blob], file.name, {
        type: 'image/jpeg',
        lastModified: Date.now()
      });
    } catch (err) {
      console.error('Image compression failed:', err);
      return file; // Return original if compression fails
    }
  };

  // Function to determine file type
  const getFileType = (file) => {
    const imageTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    const documentTypes = [
      'application/pdf', 
      'application/msword', 
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain',
      'text/csv'
    ];

    if (imageTypes.includes(file.type)) return 'image';
    if (documentTypes.includes(file.type)) return 'document';
    return 'other';
  };
  
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    // Check file size - limit to 20MB for all files
    if (file.size > 20 * 1024 * 1024) {
      setError("File is too large (max 20MB)");
      event.target.value = '';
      return;
    }

    setUploading(true);
    setError(null);
    setProgress(0);
    
    // Determine file type
    const type = getFileType(file);
    setFileType(type);
    
    try {
      // Validate the model supports required analysis
      const supportedModels = ['gemini', 'claude'];
      const modelToUse = supportedModels.includes(selectedModel) ? selectedModel : 'gemini';
      
      console.log(`📄 Uploading ${type} for analysis with model: ${modelToUse}`);
      
      // Process file based on type
      let processedFile = file;
      if (type === 'image') {
        processedFile = await compressImage(file);
      }
      
      console.log(`Uploading ${type}: ${processedFile.size / 1024 / 1024} MB`);
      
      // Create form data
      const formData = new FormData();
      
      // Choose the appropriate endpoint based on file type
      let apiEndpoint;
      
      if (type === 'image') {
        apiEndpoint = 'http://localhost:8000/chat_api/analyze_image/';
        formData.append('image', processedFile);
      } else {
        apiEndpoint = 'http://localhost:8000/chat_api/analyze_document/';
        formData.append('document', processedFile);
      }
      
      formData.append('model', modelToUse);
      formData.append('filename', file.name);
      
      // Add a temporary message to the chat showing that we're analyzing the file
      const tempMessage = `_Analyzing your ${type} "${file.name}"..._`;
      onResult(tempMessage, true, true); // true for autoSend, true for isTemporary
      
      // Make request to backend analysis endpoint with increased timeout
      const response = await axios.post(
        apiEndpoint,
        formData, 
        {
          timeout: 120000, // 2 minute timeout for large file processing
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          onUploadProgress: (progressEvent) => {
            const percentCompleted = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            setProgress(percentCompleted);
          }
        }
      );
      
      console.log('Server response:', response.data);
      
      // Process response based on file type and response format
      if (!response.data) {
        throw new Error("Empty response from server");
      }
      
      let messageContent = '';
      
      // Check for image_base64 and analysis fields which should be in all responses
      if (response.data.image_base64 && response.data.analysis) {
        // Handle standardized response format
        const imageId = `img-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
        let imageMarkdown = '';
        
        // Only include image in the message if it's an image file
        if (type === 'image') {
          imageMarkdown = `![Uploaded Image](image://${imageId})`;
          // Store the image data temporarily
          sessionStorage.setItem(imageId, response.data.image_base64);
        }
        
        // Get analysis from the response
        const analysis = response.data.analysis;
        
        // Ensure analysis has the expected format
        if (!analysis.description) {
          console.error("Missing description in analysis:", analysis);
          analysis.description = `Analysis of ${file.name}`;
        }
        
        // Format the analysis text as a conversational AI message
        if (type === 'image') {
          messageContent = `
I've analyzed the image you uploaded. Here's what I found:

${imageMarkdown ? `${imageMarkdown}\n\n` : ''}
${analysis.description}

${analysis.labels && analysis.labels.length ? `\n**Labels:** ${analysis.labels.join(', ')}` : ''}
${analysis.text ? `\n**Text detected:** ${analysis.text}` : ''}
${analysis.objects && analysis.objects.length ? `\n**Objects identified:** ${analysis.objects.join(', ')}` : ''}

You can ask me questions about this image if you'd like to know more.
          `.trim();
        } else {
          // Document analysis
          messageContent = `
I've analyzed the document "${file.name}" you uploaded.

${analysis.description}

${analysis.text ? `\n**Content preview:**\n\`\`\`\n${analysis.text}\n\`\`\`` : ''}
${analysis.labels && analysis.labels.length ? `\n**Key points:**\n${analysis.labels.map(point => `- ${point}`).join('\n')}` : ''}

Feel free to ask me any questions about this document.
          `.trim();
        }
      } 
      else if (response.data.success && response.data.analysis) {
        // Handle older format responses
        const analysis = response.data.analysis;
        let resultText;
        
        if (typeof analysis === 'string') {
          resultText = analysis;
        } else if (analysis.summary) {
          resultText = analysis.summary;
        } else {
          resultText = JSON.stringify(analysis);
        }
        
        // Format as a conversational AI message
        if (type === 'image') {
          const imageURL = URL.createObjectURL(file);
          const imageId = `img-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
          sessionStorage.setItem(imageId, imageURL);
          
          messageContent = `
I've analyzed your image. Here's what I found:

![Uploaded Image](image://${imageId})

${resultText}

Is there anything specific about this image you'd like me to explain?
          `.trim();
          
        } else {
          messageContent = `
I've analyzed your document "${file.name}".

${resultText}

Is there anything specific from this document you'd like me to explain?
          `.trim();
        }
      } else {
        console.error("Invalid response format:", response.data);
        throw new Error("Invalid response format from server. Check console for details.");
      }
      
      // Send the analysis as a bot message in the chat
      onResult(messageContent, true); // true to autoSend
      console.log(`✅ ${type} analysis complete and sent to chat`);
      
    } catch (error) {
      console.error(`Error processing ${fileType || 'file'}:`, error);
      let errorMessage = error.response?.data?.detail || error.message;
      
      // Add more helpful error messages
      if (errorMessage === 'Not Found' && fileType !== 'image') {
        errorMessage = "Document analysis endpoint not found. Make sure the backend server supports document analysis.";
      }
      
      setError(`File analysis failed: ${errorMessage}`);
      
      // Also send error as a message in the chat
      const errorContent = `❌ I couldn't analyze your ${fileType || 'file'}: ${errorMessage}`;
      onResult(errorContent, true);
      
      if (onError) {
        onError(errorMessage);
      }
    } finally {
      setUploading(false);
      setFileType(null);
      // Clear the input so the same file can be selected again
      event.target.value = '';
    }
  };

  // Determine which icon to show based on file type
  const getUploadIcon = () => {
    if (uploading) {
      return <CircularProgress size={24} variant="determinate" value={progress || 0} />;
    }
    
    return <Badge badgeContent="+" color="primary"><ImageIcon /></Badge>;
  };

  return (
    <>
      <input
        type="file"
        accept="image/jpeg,image/png,image/gif,image/webp,application/pdf,text/plain,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/csv"
        id="file-upload"
        style={{ display: 'none' }}
        onChange={handleFileUpload}
        disabled={disabled || uploading}
      />
      <Tooltip title={`Upload an image or document for ${selectedModel || 'AI'} analysis`}>
        <label htmlFor="file-upload">
          <IconButton 
            component="span"
            disabled={disabled || uploading}
            className="upload-button"
          >
            {getUploadIcon()}
          </IconButton>
        </label>
      </Tooltip>
      
      <Snackbar
        open={!!error}
        autoHideDuration={6000}
        onClose={() => setError(null)}
      >
        <Alert onClose={() => setError(null)} severity="error" sx={{ width: '100%' }}>
          {error}
        </Alert>
      </Snackbar>
    </>
  );
};

export default ImageUploader;
