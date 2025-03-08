import React, { useState, useEffect, useRef } from 'react';
import { IconButton, Tooltip } from '@mui/material';
import MicIcon from '@mui/icons-material/Mic';
import MicOffIcon from '@mui/icons-material/MicOff';
import './VoiceInput.css';

const VoiceInput = ({ onTranscript, disabled, theme, autoSend = true }) => {
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState(null);
  
  // Use refs to avoid dependency cycles in useEffect
  const recognitionRef = useRef(null);
  const transcriptRef = useRef('');

  // Initialize speech recognition
  useEffect(() => {
    // Check if browser supports speech recognition
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (SpeechRecognition) {
      const recognitionInstance = new SpeechRecognition();
      
      // Configure recognition
      recognitionInstance.continuous = true;
      recognitionInstance.interimResults = true;
      recognitionInstance.lang = 'en-US';
      
      // Set up event handlers
      recognitionInstance.onstart = () => {
        setIsListening(true);
        setError(null);
      };
      
      recognitionInstance.onresult = (event) => {
        const currentTranscript = Array.from(event.results)
          .map(result => result[0].transcript)
          .join('');
        
        // Update the ref instead of state to avoid re-renders
        transcriptRef.current = currentTranscript;
      };
      
      recognitionInstance.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setError(`Error: ${event.error}`);
        setIsListening(false);
      };
      
      recognitionInstance.onend = () => {
        // Only call the callback if we have a transcript
        if (autoSend && transcriptRef.current) {
          onTranscript(transcriptRef.current);
          transcriptRef.current = '';
        }
        setIsListening(false);
      };
      
      recognitionRef.current = recognitionInstance;
    } else {
      setError('Speech recognition not supported in this browser');
    }
    
    // Cleanup
    return () => {
      const recognition = recognitionRef.current;
      if (recognition) {
        try {
          recognition.stop();
        } catch (e) {
          console.error('Error stopping recognition:', e);
        }
      }
    };
  }, [autoSend, onTranscript]); // Remove transcript from dependencies

  // Toggle listening
  const toggleListening = () => {
    const recognition = recognitionRef.current;
    
    if (!recognition) return;

    if (isListening) {
      recognition.stop();
      // Send the final transcript to parent component if not in autoSend mode
      if (!autoSend && transcriptRef.current) {
        onTranscript(transcriptRef.current);
        transcriptRef.current = '';
      }
    } else {
      try {
        transcriptRef.current = '';
        recognition.start();
      } catch (error) {
        console.error('Recognition error:', error);
        
        // If recognition is already started, stop and restart
        if (error.name === 'NotAllowedError') {
          setError('Microphone access denied. Please allow microphone access.');
        } else {
          try {
            recognition.stop();
            setTimeout(() => {
              try {
                recognition.start();
              } catch (e) {
                setError('Could not start speech recognition');
                console.error('Failed to restart recognition:', e);
              }
            }, 100);
          } catch (stopError) {
            console.error('Error stopping recognition:', stopError);
          }
        }
      }
    }
  };

  return (
    <div className="voice-input-container">
      <Tooltip title={isListening ? "Stop recording" : "Start voice input"}>
        <IconButton
          className={`voice-button ${isListening ? 'recording' : ''}`}
          onClick={toggleListening}
          disabled={disabled || !recognitionRef.current}
          aria-label="Voice input"
        >
          {isListening ? <MicOffIcon /> : <MicIcon />}
        </IconButton>
      </Tooltip>
      
      {isListening && (
        <div className={`voice-status ${theme === 'dark' ? 'dark' : 'light'}`}>
          <div className="pulse-animation">
            <div className="pulse"></div>
          </div>
          <span className="recording-text">Listening...</span>
        </div>
      )}
      
      {error && (
        <div className="voice-error">
          {error}
        </div>
      )}
    </div>
  );
};

export default VoiceInput;
