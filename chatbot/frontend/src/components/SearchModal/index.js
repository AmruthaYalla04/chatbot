import React, { useState, useEffect } from 'react';
import { 
  Modal, 
  TextField, 
  IconButton, 
  List, 
  ListItem, 
  ListItemText,
  Typography,
  Paper,
  Box
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import CloseIcon from '@mui/icons-material/Close';
import HistoryIcon from '@mui/icons-material/History';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
// import './SearchModal.css';

const SearchModal = ({ isOpen, onClose, threads = [], onSelectResult }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [recentThreads, setRecentThreads] = useState([]);

  useEffect(() => {
    if (Array.isArray(threads) && threads.length > 0) {
      // Get 5 most recent threads
      const sortedThreads = [...threads]
        .filter(thread => thread && thread.title) // Add null check
        .sort((a, b) => {
          const dateA = new Date(a.updatedAt || a.createdAt || 0);
          const dateB = new Date(b.updatedAt || b.createdAt || 0);
          return dateB - dateA;
        })
        .slice(0, 5);
      setRecentThreads(sortedThreads);
    } else {
      setRecentThreads([]);
    }
  }, [threads]);

  const handleSearch = (e) => {
    setSearchTerm(e.target.value);
  };

  const filteredThreads = searchTerm.trim()
    ? (Array.isArray(threads) ? threads : []).filter(thread => 
        thread && thread.title && thread.title.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : recentThreads;

  return (
    <Modal
      open={isOpen}
      onClose={onClose}
      className="search-modal"
    >
      <Paper className="search-content">
        <Box className="search-header">
          <SearchIcon color="action" />
          <TextField
            autoFocus
            fullWidth
            value={searchTerm}
            onChange={handleSearch}
            placeholder="Search conversations..."
            variant="standard"
            InputProps={{
              disableUnderline: true,
              className: 'search-input'
            }}
          />
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>

        <Box className="search-results">
          {!searchTerm && (
            <Typography variant="subtitle2" className="section-title">
              <AccessTimeIcon fontSize="small" />
              Recent Conversations
            </Typography>
          )}

          <List>
            {filteredThreads.length === 0 ? (
              <ListItem>
                <ListItemText 
                  primary={searchTerm ? "No matches found" : "No recent conversations"}
                  secondary={searchTerm ? "Try different keywords" : null}
                />
              </ListItem>
            ) : (
              filteredThreads.map(thread => (
                <ListItem
                  key={thread.id}
                  button
                  onClick={() => {
                    onSelectResult(thread.id);
                    onClose();
                  }}
                >
                  <ListItemText
                    primary={thread.title}
                    secondary={new Date(thread.updatedAt || thread.createdAt).toLocaleDateString()}
                  />
                </ListItem>
              ))
            )}
          </List>
        </Box>
      </Paper>
    </Modal>
  );
};

export default SearchModal;
