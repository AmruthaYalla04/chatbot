import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { useTheme } from './context/ThemeContext';
import './Chat.css';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import { data as emojiData } from 'emoji-mart';
import emojiRegex from 'emoji-regex';
import { 
  Paper, 
  IconButton, 
  Button, 
  TextField, 
  Divider,
  Avatar,
  CircularProgress
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import SearchIcon from '@mui/icons-material/Search';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import RestoreIcon from '@mui/icons-material/Restore';
import EditIcon from '@mui/icons-material/Edit';
import SendIcon from '@mui/icons-material/Send';
import LogoutIcon from '@mui/icons-material/Logout';
import MenuIcon from '@mui/icons-material/Menu';
import ImageIcon from '@mui/icons-material/Image';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import VoiceInput from './components/VoiceInput';
import ImageUploader from './components/ImageUploader';

// Configure marked to enable tables and other features
marked.setOptions({
  gfm: true,  // GitHub Flavored Markdown
  breaks: true,
  tables: true,
  smartLists: true,
  smartypants: true
});

// Add a function to safely render markdown
const renderMarkdown = (content) => {
  // Replace Unicode emojis with spans for better styling
  const regex = emojiRegex();
  const contentWithStyledEmojis = content.replace(regex, (match) => 
    `<span class="emoji">${match}</span>`
  );

  const rawMarkup = marked(contentWithStyledEmojis);
  const cleanMarkup = DOMPurify.sanitize(rawMarkup, {
    ALLOWED_TAGS: ['p', 'b', 'i', 'em', 'strong', 'h1', 'h2', 'h3', 'table', 'tr', 'td', 'th', 'thead', 'tbody', 'img', 'a', 'ul', 'ol', 'li', 'code', 'pre', 'span'],
    ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'class']
  });
  return cleanMarkup;
};

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

function Chat({ setIsAuthenticated }) {
  const { theme } = useTheme(); // Use the theme context
  
  const [profileData, setProfileData] = useState(() => {
    try {
      const loginMethod = localStorage.getItem('login_method');
      const image = localStorage.getItem('profile_image');
      const displayName = localStorage.getItem('display_name');
      const username = localStorage.getItem('username');
      const email = localStorage.getItem('email');
      
      // Create a complete profile object with all available data
      return {
        image: image && image !== 'null' && image !== 'undefined' ? image : null,
        name: displayName || username || (email ? email.split('@')[0] : 'User'),
        email: email || '',
        username: username || '',
        fullName: displayName || username || 'User',
        loginMethod: loginMethod || 'email'
      };
    } catch (error) {
      console.error('Error initializing profile data:', error);
      return {
        image: null,
        name: 'User',
        email: '',
        username: '',
        fullName: 'User',
        loginMethod: 'unknown'
      };
    }
  });

  const fetchUserProfile = useCallback(async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return;
      
      const response = await axios.get('http://localhost:8000/users/me', {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.data) {
        // Update profile data with server response
        // Get profile image from localStorage as Google might store it there
        const profileImage = localStorage.getItem('profile_image');
        
        setProfileData(prev => ({
          ...prev,
          name: response.data.display_name || response.data.username || prev.name,
          username: response.data.username || prev.username,
          email: response.data.email || prev.email,
          image: profileImage && profileImage !== 'null' ? profileImage : prev.image
        }));
      }
    } catch (error) {
      console.error('Failed to fetch user profile:', error);
    }
  }, []);

  useEffect(() => {
    fetchUserProfile();
  }, [fetchUserProfile]);

  const [threads, setThreads] = useState([]);
  const [selectedThreadId, setSelectedThreadId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [newThreadTitle, setNewThreadTitle] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [editingThreadId, setEditingThreadId] = useState(null);
  const [editThreadTitle, setEditThreadTitle] = useState('');
  const [editingMessageId, setEditingMessageId] = useState(null);
  const [editMessageContent, setEditMessageContent] = useState('');
  const [showSearch, setShowSearch] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [showDeleted, setShowDeleted] = useState(false);
  const [deletedThreads, setDeletedThreads] = useState([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => {
    // Start with sidebar closed on all screens for consistency
    return false;
  });
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);
  const [selectedModel, setSelectedModel] = useState(() => {
    // Load from localStorage or default to 'openai'
    const savedModel = localStorage.getItem('preferred_model');
    // Ensure we have a valid value
    return ['openai', 'gemini', 'claude'].includes(savedModel) ? savedModel : 'openai';
  });
  
  useEffect(() => {
    console.log(`🔧 Active model set to: ${selectedModel}`);
  }, [selectedModel]);
  
  const navigate = useNavigate();
  const userId = parseInt(localStorage.getItem('user_id')) || 1;
  const token = localStorage.getItem('access_token');

  const fetchChatThreads = useCallback(async () => {
    setLoading(true);
    try {
      const [activeResponse, deletedResponse] = await Promise.all([
        axios.get(`http://localhost:8000/chat_api/chat/`, {
          params: { user_id: userId, show_deleted: false }
        }),
        axios.get(`http://localhost:8000/chat_api/chat/`, {
          params: { user_id: userId, show_deleted: true }
        })
      ]);

      setThreads(activeResponse.data);
      setDeletedThreads(deletedResponse.data.filter(thread => thread.is_deleted));
      setError(null);
    } catch (error) {
      console.error("Error fetching chat threads", error);
      setError("Failed to load chat threads");
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      navigate('/login');
      return;
    }
    fetchChatThreads();
  }, [navigate, fetchChatThreads]);

  // Improved logout function to ensure clean transition to login page
const handleLogout = useCallback(() => {
  try {
    // Immediately prevent any further user interaction
    document.body.style.pointerEvents = 'none';
    document.body.style.cursor = 'wait';
    
    // Create and show overlay immediately to prevent UI flash
    const overlay = document.createElement('div');
    overlay.className = 'logout-overlay';
    overlay.style.position = 'fixed';
    overlay.style.top = '0';
    overlay.style.left = '0';
    overlay.style.right = '0';
    overlay.style.bottom = '0';
    overlay.style.backgroundColor = 'rgba(0,0,0,0.3)';
    overlay.style.zIndex = '9999';
    overlay.style.opacity = '1';  // Start visible immediately
    document.body.appendChild(overlay);
    
    // Immediately stop any pending API requests
    const controller = window.AbortController ? new AbortController() : null;
    if (controller) {
      controller.abort();
    }
    
    // Synchronously clear all authentication data (no delays)
    localStorage.clear();
    sessionStorage.clear();
    
    // Update authentication state if available
    if (setIsAuthenticated) {
      setIsAuthenticated(false);
    }
    
    // Use a hard redirect for clean state reset, bypassing React Router
    window.location.replace('/login');  // replace() won't add to browser history
    
    // As a safeguard, add a timeout to force redirect if the above doesn't work
    setTimeout(() => {
      window.location.href = '/login';
    }, 100);
    
  } catch (error) {
    console.error('Logout error:', error);
    // Emergency fallback - force reload to login
    window.location.href = '/login';
  }
}, [setIsAuthenticated]);

  // Add cleanup effect
  useEffect(() => {
    return () => {
      // Cleanup on unmount if needed
    };
  }, []);

  // Add useEffect to handle token expiration
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      handleLogout();
    }
  }, [handleLogout]);

  useEffect(() => {
    fetchChatThreads();
  }, [fetchChatThreads]);

  const fetchMessages = async (threadId) => {
    setLoading(true);
    try {
      console.log(`Fetching messages for thread ${threadId}`);
      const response = await axios.get(`http://localhost:8000/chat_api/chat/${threadId}/messages/`, {
        params: { user_id: userId }
      });
      console.log('Messages received:', response.data);
      setMessages(response.data);
      setError(null);
    } catch (error) {
      console.error("Error fetching messages", error);
      if (error.response && error.response.status === 404) {
        setError("Chat thread not found. Please select a different thread.");
      } else {
        setError("Failed to load messages. Please try again later.");
      }
      setMessages([]);
    } finally {
      setLoading(false);
    }
  };

  const createNewChat = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await axios.post(`http://localhost:8000/chat_api/chat/create_thread/`, {
        user_id: userId,
        title: "New Conversation" // Use more conversational default title
      });

      // Validate response format to catch issues early
      if (!response.data || typeof response.data !== 'object') {
        throw new Error("Invalid response format from server");
      }
      
      if (!response.data.id) {
        throw new Error("Server response missing thread ID");
      }

      setThreads(prevThreads => [response.data, ...prevThreads]); // Add new thread at the beginning of list
      setSelectedThreadId(response.data.id);
      setMessages([]);
    } catch (error) {
      console.error('Error creating new chat:', error);
      
      // More detailed error handling
      const errorMsg = error.response?.data?.detail || error.message;
      setError(`Failed to create new chat: ${errorMsg}`);
      
      // Handle specific error scenarios
      if (error.response?.status === 500) {
        setError("Server error while creating chat thread. Please try again in a moment.");
      } else if (error.response?.status === 401) {
        // Session might be expired, trigger logout
        handleLogout();
      } else if (!navigator.onLine) {
        setError("Network connection issue. Please check your internet connection.");
      }
    } finally {
      setLoading(false);
    }
  };

  // Helper function to generate a good title from message content
  const generateTitleFromMessage = (message) => {
    // Remove special characters that might cause issues
    let cleanMessage = message
      .replace(/[^\w\s.,?!-]/g, ' ') // Replace problematic special chars with spaces
      .replace(/\s+/g, ' ')          // Replace multiple spaces with single space
      .trim();
    
    // If message starts with a question, use that as the title
    const questionMatch = cleanMessage.match(/^.*?(\w.*?\?)/);
    if (questionMatch && questionMatch[1].length <= 40) {
      return questionMatch[1];
    }
    
    // Otherwise take the first 40 chars or first sentence, whichever is shorter
    const firstSentence = cleanMessage.split(/[.!?]/, 1)[0].trim();
    if (firstSentence.length <= 40) {
      return firstSentence;
    }
    
    return cleanMessage.substring(0, 37) + '...';
  };

  // Update the sendMessage function to ensure proper model handling and fix the duplicate key error
const sendMessage = async () => {
  // Make sure we have text to send
  if (!newMessage || !newMessage.trim()) {
    console.warn("Attempted to send empty message");
    return;
  }
  
  setLoading(true);
  setError(null);

  try {
    let currentThreadId = selectedThreadId;
    let isNewThread = false;
    let shouldUpdateTitle = false;
    
    // Create new thread if none selected
    if (!currentThreadId) {
      try {
        const threadResponse = await axios.post(`http://localhost:8000/chat_api/chat/create_thread/`, {
          user_id: userId,
          title: "New Conversation"
        });
        
        // Validate response format
        if (!threadResponse.data || typeof threadResponse.data !== 'object' || !threadResponse.data.id) {
          throw new Error("Invalid thread creation response");
        }
        
        currentThreadId = threadResponse.data.id;
        setSelectedThreadId(currentThreadId);
        setThreads([threadResponse.data, ...threads]);
        isNewThread = true;
      } catch (threadError) {
        console.error("Thread creation failed:", threadError);
        setError(`Failed to create thread: ${threadError.message}`);
        setLoading(false);
        return; // Exit early if thread creation fails
      }
    } else {
      // Check if this is the first message in an existing thread
      const existingThread = threads.find(t => t.id === currentThreadId);
      if (existingThread && existingThread.title === "New Conversation") {
        shouldUpdateTitle = true;
      }
    }

    // Ensure model is properly normalized but preserve the exact selected model
    const modelToUse = (selectedModel || 'openai').toLowerCase().trim();
    
    // Log the selected model with more visibility for debugging
    console.log(`%c🤖 Sending message with MODEL: ${modelToUse}`, 'color: blue; font-weight: bold; font-size: 14px;');
    
    // Show user which model is being used
    if (loading === false) {
      // Add temporary model message to the UI with a unique ID based on timestamp
      const tempId = `temp-loading-${Date.now()}`;
      const modelDisplayName = 
        modelToUse === 'gemini' ? 'Gemini' : 
        modelToUse === 'claude' ? 'Claude' :
        'ChatGPT';
        
      const tempMessages = [...messages, {
        id: tempId,
        role: 'assistant',
        content: `Generating response using ${modelDisplayName}...`,
        model: modelToUse,
        isLoading: true
      }];
      setMessages(tempMessages);
    }

    // Send the message
    const response = await axios.post(`http://localhost:8000/chat_api/chat/${currentThreadId}/message/`, {
      user_id: userId,
      message: newMessage,
      model: modelToUse,
      update_title: isNewThread || shouldUpdateTitle,
      suggested_title: generateTitleFromMessage(newMessage)
    });

    // Debug logging for model response
    const assistantMessages = response.data.filter(msg => msg.role === 'assistant');
    if (assistantMessages.length > 0) {
      const lastMessage = assistantMessages[assistantMessages.length - 1];
      console.log(`%c🔍 Response from MODEL: ${lastMessage.model || 'unknown'}`, 
        'color: green; font-weight: bold; font-size: 14px;');
      
      // Log model verification for debugging
      const isGemini = /gemini|google/i.test(lastMessage.content);
      const isOpenAI = /chatgpt|openai/i.test(lastMessage.content);
      const isClaude = /claude|anthropic/i.test(lastMessage.content);
      
      let detectedModel = "Unknown";
      if (isGemini) detectedModel = "Gemini";
      if (isOpenAI) detectedModel = "ChatGPT";
      if (isClaude) detectedModel = "Claude";
      
      console.log(`%c🔍 Model detection: ${detectedModel}`, 
        `color: ${detectedModel.toLowerCase() === modelToUse ? 'green' : 'red'}; 
         font-weight: bold; font-size: 14px;`);
    }

    setMessages(response.data);
    setNewMessage('');
    
    // Update thread title if needed
    if (isNewThread || shouldUpdateTitle) {
      const newTitle = generateTitleFromMessage(newMessage);
      
      await axios.put(`http://localhost:8000/chat_api/chat/${currentThreadId}/update/`, {
        user_id: userId,
        title: newTitle
      });
      
      const updatedThreads = threads.map(thread =>
        thread.id === currentThreadId ? { ...thread, title: newTitle } : thread
      );
      setThreads(updatedThreads);
    } else {
      await fetchChatThreads();
    }
  } catch (error) {
    console.error("Error sending message:", error);
    setError(`Failed to send message: ${error.response?.data?.detail || error.message}`);
    
    // Generate a unique error ID based on timestamp to avoid duplicate keys
    const errorId = `error-msg-${Date.now()}`;
    
    // Show error in chat without removing existing messages
    setMessages(prevMessages => [
      ...prevMessages.filter(m => !m.isLoading), // Remove any loading indicators
      {
        id: errorId,
        role: 'assistant',
        content: `Error: ${error.response?.data?.detail || error.message}. Please try again.`,
        model: selectedModel,
        isError: true
      }
    ]);
  } finally {
    setLoading(false);
  }
};

  const updateThreadTitle = async (threadId, newTitle) => {
    if (!newTitle.trim()) return;
    
    try {
      const response = await axios.put(`http://localhost:8000/chat_api/chat/${threadId}/update/`, {
        user_id: userId,
        title: newTitle
      });
      
      const updatedThreads = threads.map(thread =>
        thread.id === threadId ? { ...thread, title: newTitle } : thread
      );
      setThreads(updatedThreads);
      setEditingThreadId(null);
    } catch (error) {
      console.error('Error updating thread:', error);
      setError(`Failed to update thread title: ${error.message}`);
    }
  };

  const deleteThread = async (threadId) => {
    if (window.confirm('Are you sure you want to delete this chat?')) {
      try {
        setLoading(true);
        await axios.delete(`http://localhost:8000/chat_api/chat/${threadId}/delete/`, {
          params: { user_id: userId }
        });
        
        if (selectedThreadId === threadId) {
          setSelectedThreadId(null);
          setMessages([]);
        }
        
        await fetchChatThreads(); // Refresh both active and deleted threads
      } catch (error) {
        setError(`Failed to delete thread: ${error.message}`);
      } finally {
        setLoading(false);
      }
    }
  };

  const restoreThread = async (threadId) => {
    try {
      setLoading(true);
      await axios.post(`http://localhost:8000/chat_api/chat/${threadId}/restore/`, null, {
        params: { user_id: userId }
      });
      await fetchChatThreads(); // Refresh both active and deleted threads
      setShowDeleted(false); // Switch back to active threads view after restore
    } catch (error) {
      setError(`Failed to restore thread: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const updateMessage = async (messageId, newContent) => {
    if (!newContent.trim()) return;
    
    setLoading(true);
    setError(null);

    try {
      // Add error handling for missing IDs
      if (!selectedThreadId || !messageId) {
        throw new Error('Missing thread ID or message ID');
      }

      // Ensure model is lowercase
      const modelToUse = selectedModel.toLowerCase();
      console.log(`📝 Updating message ${messageId} with model: ${modelToUse}`);
      
      const response = await axios.put(
        `http://localhost:8000/chat_api/chat/${selectedThreadId}/message/${messageId}/`, 
        {
          user_id: userId,
          message: newContent,
          model: modelToUse  // Send lowercase model name
        }
      );

      // Verify response contains updated messages
      if (Array.isArray(response.data)) {
        setMessages(response.data);
      } else {
        throw new Error('Invalid response format');
      }
      
      setEditingMessageId(null);
      setEditMessageContent('');
    } catch (error) {
      console.error('Error updating message:', error);
      setError(`Failed to update message: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };


  const fetchSearchThreads = async (query) => {
    try {
      const response = await axios.get(`http://localhost:8000/chat_api/chat/`, {
        params: { 
          user_id: userId,
          search: query 
        }
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching search results:', error);
      return [];
    }
  };

  const handleSearch = async (query) => {
    setSearchQuery(query);
    if (query.trim() === '') {
      setSearchResults([]);
      return;
    }
    
    // First show local results immediately
    const localResults = threads.filter(thread => 
      thread.title.toLowerCase().includes(query.toLowerCase())
    );
    setSearchResults(localResults);
    
    // Then fetch from server
    try {
      const serverResults = await fetchSearchThreads(query);
      setSearchResults(serverResults);
    } catch (error) {
      console.error('Error in search:', error);
    }
  };

  const handleSelectSearchResult = (threadId) => {
    setSelectedThreadId(threadId);
    fetchMessages(threadId);
    setShowSearch(false);
    setSearchQuery('');
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Add authentication check
  useEffect(() => {
    const checkAuth = () => {
      const token = localStorage.getItem('access_token');
      if (!token) {
        window.location.href = '/login';
        return;
      }
      
      // Initialize profile data
      const loginData = {
        image: localStorage.getItem('profile_image'),
        name: localStorage.getItem('display_name') || localStorage.getItem('username'),
        email: localStorage.getItem('email'),
        fullName: localStorage.getItem('username')
      };
      
      setProfileData(loginData);
    };

    checkAuth();
  }, []);

  // Add ref for messages container
  const messagesContainerRef = useRef(null);
  const resizeObserverRef = useRef(null);

  // Update scroll handling with debounce and cleanup
  useEffect(() => {
    const scrollToBottom = debounce(() => {
      if (messagesContainerRef.current) {
        messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
      }
    }, 100);

    // Setup ResizeObserver with error handling
    if (messagesContainerRef.current) {
      resizeObserverRef.current = new ResizeObserver((entries) => {
        try {
          scrollToBottom();
        } catch (error) {
          console.warn('ResizeObserver error handled:', error);
        }
      });

      resizeObserverRef.current.observe(messagesContainerRef.current);
    }

    // Cleanup function
    return () => {
      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect();
      }
    };
  }, [messages]);

  // Update mobile handling
  const handleResize = useCallback(debounce(() => {
    const isMobileView = window.innerWidth <= 768;
    setIsMobile(isMobileView);
    if (!isMobileView) {
      setIsSidebarOpen(true);
    }
  }, 100), []);

  useEffect(() => {
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [handleResize]);

  // Add message edit handler
  const handleEditMessage = (messageId, content) => {
    setEditingMessageId(messageId);
    setEditMessageContent(content);
  };

  // Add resize handler
  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
      if (window.innerWidth > 768) {
        setIsSidebarOpen(true);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const toggleSidebar = useCallback(() => {
    setIsSidebarOpen(prev => !prev);
  }, []);

  // Update mobile handling with auto-close
  useEffect(() => {
    const handleResize = () => {
      const isMobileView = window.innerWidth <= 768;
      setIsMobile(isMobileView);
      if (isMobileView) {
        setIsSidebarOpen(false); // Auto-close on mobile
      } else {
        setIsSidebarOpen(true); // Always open on desktop
      }
    };

    handleResize(); // Initial check
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Update sidebar toggle to auto-close on mobile selection
  const handleThreadSelect = (threadId) => {
    setSelectedThreadId(threadId);
    fetchMessages(threadId);
    if (window.innerWidth <= 768) {
      setIsSidebarOpen(false); // Auto-close sidebar on mobile after selection
    }
  };

  // Add useEffect to handle initial state on desktop screens
  useEffect(() => {
    // Show sidebar on desktop on initial load
    const isDesktop = window.innerWidth > 768;
    if (isDesktop) {
      setIsSidebarOpen(true);
      // Add a CSS class to sidebar for initial-desktop state
      const sidebarEl = document.querySelector('.sidebar');
      if (sidebarEl) sidebarEl.classList.add('initial-desktop');
    }
  }, []);

  // Add a new function to handle voice input transcript
  const handleVoiceInput = (transcript) => {
    if (transcript.trim()) {
      // Append transcript to current message or set as new message
      setNewMessage((prev) => {
        const separator = prev.trim() ? ' ' : '';
        return prev.trim() + separator + transcript.trim();
      });
    }
  };

  const handleModelChange = (newModel) => {
    console.log(`📌 Changing model from ${selectedModel} to: ${newModel}`);
    
    // Validate model
    if (!['openai', 'gemini', 'claude'].includes(newModel)) {
      console.warn(`Invalid model: ${newModel}, defaulting to 'openai'`);
      newModel = 'openai';
    }
    
    // Update state and localStorage
    setSelectedModel(newModel);
    localStorage.setItem('preferred_model', newModel);
    
    // Add visual feedback that the model was changed
    const header = document.querySelector('.chat-header');
    if (header) {
      header.classList.add('model-changed');
      setTimeout(() => header.classList.remove('model-changed'), 1000);
    }
  };

  const [imageUploading, setImageUploading] = useState(false);

  // Update the handleImageResult function to check for Claude model
const handleImageResult = (resultData, autoSend = false) => {
  // Both Claude and Gemini support image analysis
  const supportsImages = ['gemini', 'claude'].includes(selectedModel);
  
  if (!supportsImages) {
    setError("The current model doesn't support image analysis. Please switch to Gemini or Claude.");
    return;
  }
  
  // Just set the message content but don't send
  if (resultData && typeof resultData === 'object' && resultData.type) {
    setNewMessage(resultData.content);
  } else {
    // Standard string result - just set the message content
    setNewMessage(resultData);
    
    // Focus the input field for easier sending
    const inputField = document.querySelector('.message-input .MuiInputBase-input');
    if (inputField) {
      inputField.focus();
    }
  }
};

  const handleImageError = (errorMessage) => {
    setError(`Image analysis failed: ${errorMessage}`);
    // Show error as a temporary message
    setNewMessage("Sorry, I couldn't analyze that image. Please try another one or try again later.");
  };

  // Add a global error handler for axios to manage API errors
useEffect(() => {
  // Add request interceptor for authentication token
  const requestInterceptor = axios.interceptors.request.use(
    config => {
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers['Authorization'] = `Bearer ${token}`;
      }
      return config;
    },
    error => Promise.reject(error)
  );
  
  // Add response interceptor for error handling
  const responseInterceptor = axios.interceptors.response.use(
    response => response,
    error => {
      // Handle session expiration
      if (error.response?.status === 401) {
        console.warn("Authentication error detected");
        // Don't call handleLogout directly from here to avoid circular dependencies
        // Instead set a flag that will trigger logout in a useEffect
        localStorage.setItem('auth_error', 'true');
        window.dispatchEvent(new Event('auth_error'));
      }
      
      // Log API errors for debugging
      if (error.response?.status === 500) {
        console.error("Server error:", error.response?.data || error.message);
      }
      
      return Promise.reject(error);
    }
  );
  
  // Listen for auth errors
  const handleAuthError = () => {
    if (localStorage.getItem('auth_error') === 'true') {
      localStorage.removeItem('auth_error');
      handleLogout();
    }
  };
  
  window.addEventListener('auth_error', handleAuthError);
  
  // Clean up interceptors and event listeners when component unmounts
  return () => {
    axios.interceptors.request.eject(requestInterceptor);
    axios.interceptors.response.eject(responseInterceptor);
    window.removeEventListener('auth_error', handleAuthError);
  };
}, [handleLogout]);

  return (
    <div className={`app-container ${theme}-theme`}>
      <Sidebar 
        createNewChat={createNewChat}
        setShowSearch={setShowSearch}
        showDeleted={showDeleted}
        setShowDeleted={setShowDeleted}
        threads={threads}
        deletedThreads={deletedThreads}
        selectedThreadId={selectedThreadId}
        onThreadSelect={handleThreadSelect}
        onThreadUpdate={updateThreadTitle}
        onThreadDelete={deleteThread}
        onThreadRestore={restoreThread}
        isMobile={isMobile}
        isOpen={isSidebarOpen}
        onToggle={toggleSidebar}
        editingThreadId={editingThreadId}
        setEditingThreadId={setEditingThreadId}
        editThreadTitle={editThreadTitle}
        setEditThreadTitle={setEditThreadTitle}
        profileData={profileData}
        handleLogout={handleLogout}
      />
      
      <div className={`chat-container ${isSidebarOpen ? 'sidebar-open' : ''}`}>
        <div className="chat-main">
          <Header 
            toggleSidebar={toggleSidebar}
            selectedModel={selectedModel}
            onModelChange={handleModelChange}
          />
          
          <div className="messages-container" ref={messagesContainerRef}>
            {!loading && messages.length === 0 && !error && (
              <div className="empty-chat">
                <h2>Welcome to the Chat!</h2>
                <p>Select a chat from sidebar or start a new conversation</p>
              </div>
            )}

            <div className="messages-list">
              {messages.map((msg) => (
                <div 
                  key={msg.id} 
                  className={`message ${msg.role === 'assistant' ? 'bot' : 'user'}`}
                >
                  <div className="message-content">
                    {editingMessageId === msg.id ? (
                      <div className="edit-message-container">
                        <TextField
                          multiline
                          fullWidth
                          value={editMessageContent}
                          onChange={(e) => setEditMessageContent(e.target.value)}
                          variant="outlined"
                          autoFocus
                          className="edit-message-input"
                        />
                        <div className="edit-message-actions">
                          <IconButton
                            className="save-edit-button"
                            onClick={() => updateMessage(msg.id, editMessageContent)}
                            size="small"
                            title="Save changes"
                          >
                            <i className="fas fa-check"></i>
                          </IconButton>
                          <IconButton
                            className="cancel-edit-button"
                            onClick={() => {
                              setEditingMessageId(null);
                              setEditMessageContent('');
                            }}
                            size="small"
                            title="Cancel editing"
                          >
                            <i className="fas fa-times"></i>
                          </IconButton>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div 
                          className="markdown-content"
                          dangerouslySetInnerHTML={{ 
                            __html: msg.role === 'assistant' ? 
                              renderMarkdown(msg.content) : 
                              msg.content 
                          }} 
                        />
                        {msg.role === 'user' && (
                          <IconButton
                            className="edit-message-button"
                            onClick={() => handleEditMessage(msg.id, msg.content)}
                            size="small"
                          >
                            <EditIcon fontSize="small" />
                          </IconButton>
                        )}
                      </>
                    )}
                  </div>
                </div>
              ))}
              {loading && <div className="message bot loading">Generating Response...</div>}
            </div>
          </div>

          <div className="message-input-container">
            <TextField
              multiline
              maxRows={4}
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message here..."
              className="message-input"
              disabled={loading}
              variant="outlined"
              fullWidth
              sx={{ 
                backgroundColor: theme === 'dark' ? 'var(--input-bg)' : 'var(--input-bg)',
                '& .MuiOutlinedInput-root': {
                  paddingRight: '96px', // Increased to accommodate both buttons
                  color: theme === 'dark' ? 'var(--input-text)' : 'var(--input-text)',
                }
              }}
              InputProps={{
                endAdornment: (
                  <div className="input-actions">
                    <ImageUploader 
                      onResult={handleImageResult} 
                      onError={handleImageError}
                      disabled={loading || imageUploading} 
                      selectedModel={selectedModel} 
                    />
                    <VoiceInput 
                      onTranscript={handleVoiceInput} 
                      disabled={loading}
                      theme={theme}
                    />
                    <IconButton
                      className={`send-icon-button ${!newMessage.trim() || loading ? 'disabled' : ''}`}
                      onClick={sendMessage}
                      disabled={!newMessage.trim() || loading}
                      size="small"
                    >
                      <SendIcon />
                    </IconButton>
                  </div>
                ),
              }}
            />
          </div>
        </div>
      </div>

      {/* Add overlay that closes sidebar when clicking outside */}
      {isSidebarOpen && (
        <div 
          className="sidebar-overlay active"
          onClick={toggleSidebar}
          aria-hidden="true"
        />
      )}

      {/* ...existing search modal code... */}
    </div>
  );
}

export default Chat;

