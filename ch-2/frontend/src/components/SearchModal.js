import React, { useState, useEffect, useRef } from 'react';
import { TextField, IconButton, Dialog, DialogTitle, DialogContent, DialogActions, Button } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import SearchIcon from '@mui/icons-material/Search';

const SearchModal = ({ 
  isOpen, 
  onClose, 
  threads, 
  searchResults, 
  onSearch, 
  onSelectResult,
  theme 
}) => {
  const [query, setQuery] = useState('');
  const inputRef = useRef(null);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      setTimeout(() => {
        inputRef.current.focus();
      }, 100);
    }
    return () => setQuery('');
  }, [isOpen]);

  useEffect(() => {
    const delaySearch = setTimeout(() => {
      if (query) {
        onSearch(query);
      }
    }, 300);

    return () => clearTimeout(delaySearch);
  }, [query, onSearch]);

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  return (
    <Dialog 
      open={isOpen} 
      onClose={onClose} 
      maxWidth="sm" 
      fullWidth
      PaperProps={{
        style: {
          backgroundColor: theme === 'dark' ? '#1a1a1a' : '#fff',
          color: theme === 'dark' ? '#f0f0f0' : '#2c1810',
          borderRadius: '12px',
        }
      }}
      BackdropProps={{
        style: {
          backdropFilter: 'blur(5px)',
          backgroundColor: 'rgba(0, 0, 0, 0.5)'
        }
      }}
    >
      <DialogTitle style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        Search Chats
        <IconButton onClick={onClose}>
          <CloseIcon sx={{ color: theme === 'dark' ? '#f0f0f0' : '#2c1810' }} />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        <TextField
          autoFocus
          margin="dense"
          placeholder="Search for conversations..."
          type="text"
          fullWidth
          variant="outlined"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          InputProps={{
            startAdornment: <SearchIcon sx={{ color: theme === 'dark' ? '#9c56ff' : '#7c4dff', mr: 1 }} />,
            style: {
              backgroundColor: theme === 'dark' ? '#282c34' : '#f5f0ff',
              borderRadius: '8px',
              color: theme === 'dark' ? '#f0f0f0' : '#2c1810',
            }
          }}
          inputRef={inputRef}
        />
        
        <div style={{ 
          marginTop: '20px', 
          maxHeight: '300px', 
          overflowY: 'auto',
          backgroundColor: theme === 'dark' ? '#1e1e24' : '#fff',
          borderRadius: '8px'
        }}>
          {searchResults.length > 0 ? (
            searchResults.map((thread) => (
              <div
                key={thread.id}
                onClick={() => onSelectResult(thread.id)}
                style={{
                  padding: '12px',
                  borderBottom: `1px solid ${theme === 'dark' ? '#3d3d46' : '#e0d4ff'}`,
                  cursor: 'pointer',
                  transition: 'background-color 0.2s',
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.backgroundColor = theme === 'dark' ? '#3d3d46' : '#f5f0ff';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.backgroundColor = theme === 'dark' ? '#282c34' : '#fff';
                }}
              >
                <div style={{ fontWeight: 'bold' }}>{thread.title}</div>
              </div>
            ))
          ) : query ? (
            <div style={{ 
              padding: '16px', 
              textAlign: 'center',
              color: theme === 'dark' ? '#a0a0a0' : '#6b6b6b' 
            }}>
              No results found
            </div>
          ) : null}
        </div>
      </DialogContent>
      <DialogActions>
        <Button 
          onClick={onClose}
          sx={{
            color: theme === 'dark' ? '#9c56ff' : '#7c4dff',
            '&:hover': {
              backgroundColor: theme === 'dark' ? 'rgba(156, 86, 255, 0.1)' : 'rgba(124, 77, 255, 0.1)',
            }
          }}
        >
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default SearchModal;
