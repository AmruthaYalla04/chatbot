import React, { useState } from 'react';
import { Button, IconButton } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import SearchIcon from '@mui/icons-material/Search';
import MenuIcon from '@mui/icons-material/Menu';
import { useTheme } from '../context/ThemeContext';
import ThreadList from './Threadlist';
import SearchModal from './SearchModal';
import SidebarFooter from './SidebarFooter';
import './Sidebar.css';

const Sidebar = ({
  createNewChat,
  setShowSearch,
  showDeleted,
  setShowDeleted,
  threads = [],
  deletedThreads,
  selectedThreadId,
  onThreadSelect,
  onThreadUpdate,
  onThreadDelete,
  onThreadRestore,
  isMobile,
  isOpen,
  onToggle,
  editingThreadId,
  setEditingThreadId,
  editThreadTitle,
  setEditThreadTitle,
  profileData,
  handleLogout
}) => {
  const [showSearchModal, setShowSearchModal] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const { theme } = useTheme();

  const handleSearch = async (query) => {
    if (!query.trim()) {
      setSearchResults([]);
      return;
    }

    // Local search in existing threads
    const results = threads.filter(thread =>
      thread.title.toLowerCase().includes(query.toLowerCase())
    );
    setSearchResults(results);
  };

  return (
    <div className={`sidebar ${isOpen ? 'open' : ''} ${theme}-sidebar`}>
      <div className="threads-header">
        {isMobile && (
          <IconButton
            className="hamburger-button"
            onClick={onToggle}
            sx={{ 
              marginRight: 1,
              color: theme === 'dark' ? '#f0f0f0' : '#2c1810'
            }}
          >
            <MenuIcon />
          </IconButton>
        )}
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          className="new-chat-button"
          onClick={createNewChat}
        >
          New Chat
        </Button>
        <IconButton 
          onClick={() => setShowSearchModal(true)}
          className="search-button"
          title="Search chats"
          sx={{ 
            color: theme === 'dark' ? '#f0f0f0' : '#2c1810',
            '&:hover': {
              backgroundColor: theme === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.04)'
            }
          }}
        >
          <SearchIcon />
        </IconButton>
      </div>

      <ThreadList 
        threads={threads}
        deletedThreads={deletedThreads}
        showDeleted={showDeleted}
        selectedThreadId={selectedThreadId}
        onThreadSelect={onThreadSelect}
        onThreadUpdate={onThreadUpdate}
        onThreadDelete={onThreadDelete}
        onThreadRestore={onThreadRestore}
        editingThreadId={editingThreadId}
        setEditingThreadId={setEditingThreadId}
        editThreadTitle={editThreadTitle}
        setEditThreadTitle={setEditThreadTitle}
        theme={theme}
      />

      <SidebarFooter 
        profileData={profileData} 
        handleLogout={handleLogout}
      />

      <SearchModal
        isOpen={showSearchModal}
        onClose={() => setShowSearchModal(false)}
        threads={threads}
        searchResults={searchResults}
        onSearch={handleSearch}
        onSelectResult={(threadId) => {
          onThreadSelect(threadId);
          setShowSearchModal(false);
        }}
        theme={theme}
      />
    </div>
  );
};

export default Sidebar;
