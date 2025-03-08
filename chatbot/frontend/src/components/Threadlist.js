import React from 'react';
import { IconButton, TextField } from '@mui/material';
import RestoreIcon from '@mui/icons-material/Restore';
import EditIcon from '@mui/icons-material/Edit';
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline'; // Add this import

const ThreadList = ({
  threads,
  deletedThreads,
  showDeleted,
  selectedThreadId,
  onThreadSelect,
  onThreadUpdate,
  onThreadDelete, // Still accept this prop for functionality
  onThreadRestore,
  editingThreadId,
  setEditingThreadId,
  editThreadTitle,
  setEditThreadTitle,
  theme
}) => {
  const threadsToDisplay = showDeleted ? deletedThreads : threads;
  
  const handleEditStart = (threadId, currentTitle) => {
    setEditingThreadId(threadId);
    setEditThreadTitle(currentTitle);
  };

  const handleEditSave = () => {
    if (editingThreadId) {
      onThreadUpdate(editingThreadId, editThreadTitle);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleEditSave();
    } else if (e.key === 'Escape') {
      setEditingThreadId(null);
    }
  };

  return (
    <div className="threads-list-container">
      {threadsToDisplay.length === 0 ? (
        <div className="empty-threads-message" style={{ padding: '20px', textAlign: 'center', color: theme === 'dark' ? '#a0a0a0' : '#6b6b6b' }}>
          {showDeleted 
            ? "No deleted chats found" 
            : "No chats yet. Start a new conversation!"}
        </div>
      ) : (
        threadsToDisplay.map(thread => (
          <div 
            key={thread.id}
            className={`thread-item ${selectedThreadId === thread.id ? 'active' : ''} ${thread.is_deleted ? 'deleted' : ''}`}
            onClick={() => !editingThreadId && onThreadSelect(thread.id)}
          >
            <div className="thread-content">
              {editingThreadId === thread.id ? (
                <TextField 
                  value={editThreadTitle}
                  onChange={(e) => setEditThreadTitle(e.target.value)}
                  onKeyDown={handleKeyPress}
                  autoFocus
                  fullWidth
                  size="small"
                  variant="outlined"
                  sx={{ 
                    fontSize: '14px',
                    '& .MuiOutlinedInput-root': {
                      borderRadius: '8px',
                      backgroundColor: theme === 'dark' ? '#282c34' : '#fff',
                      color: theme === 'dark' ? '#f0f0f0' : 'inherit'
                    }
                  }}
                  onClick={(e) => e.stopPropagation()}
                />
              ) : (
                <div className="thread-title" title={thread.title}>
                  {thread.title}
                </div>
              )}
            </div>
            
            <div className="thread-actions">
              {editingThreadId === thread.id ? (
                <>
                  <IconButton 
                    className="icon-button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleEditSave();
                    }}
                    size="small"
                    sx={{
                      color: theme === 'dark' ? '#9c56ff' : '#7c4dff',
                      '&:hover': {
                        backgroundColor: theme === 'dark' ? 'rgba(156, 86, 255, 0.1)' : 'rgba(124, 77, 255, 0.1)',
                      }
                    }}
                  >
                    <CheckIcon fontSize="small" />
                  </IconButton>
                  <IconButton 
                    className="icon-button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setEditingThreadId(null);
                    }}
                    size="small"
                    sx={{
                      color: theme === 'dark' ? '#a0a0a0' : '#6b6b6b',
                      '&:hover': {
                        backgroundColor: theme === 'dark' ? 'rgba(160, 160, 160, 0.1)' : 'rgba(107, 107, 107, 0.1)',
                      }
                    }}
                  >
                    <CloseIcon fontSize="small" />
                  </IconButton>
                </>
              ) : (
                <>
                  {!showDeleted && (
                    <>
                      <IconButton 
                        className="edit-button icon-button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleEditStart(thread.id, thread.title);
                        }}
                        size="small"
                        sx={{
                          color: theme === 'dark' ? '#9c56ff' : '#7c4dff',
                          '&:hover': {
                            backgroundColor: theme === 'dark' ? 'rgba(156, 86, 255, 0.1)' : 'rgba(124, 77, 255, 0.1)',
                          }
                        }}
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                      
                      {/* Add delete button */}
                      {onThreadDelete && (
                        <IconButton 
                          className="delete-button icon-button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onThreadDelete(thread.id);
                          }}
                          size="small"
                          sx={{
                            color: theme === 'dark' ? '#ff5252' : '#f44336',
                            '&:hover': {
                              backgroundColor: theme === 'dark' ? 'rgba(255, 82, 82, 0.1)' : 'rgba(244, 67, 54, 0.1)',
                            }
                          }}
                        >
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      )}
                    </>
                  )}
                  
                  {showDeleted && (
                    <IconButton 
                      className="restore-button icon-button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onThreadRestore(thread.id);
                      }}
                      size="small"
                      sx={{
                        color: theme === 'dark' ? '#4caf50' : '#28a745',
                        '&:hover': {
                          backgroundColor: theme === 'dark' ? 'rgba(76, 175, 80, 0.1)' : 'rgba(40, 167, 69, 0.1)',
                        }
                      }}
                    >
                      <RestoreIcon fontSize="small" />
                    </IconButton>
                  )}
                </>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
};

export default ThreadList;
