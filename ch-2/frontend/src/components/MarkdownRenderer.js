import React, { useEffect, useMemo, useRef } from 'react';
import DOMPurify from 'dompurify';
import { marked } from 'marked';
import emojiRegex from 'emoji-regex';
import hljs from 'highlight.js';
import 'highlight.js/styles/github-dark.css';

const MarkdownRenderer = ({ content }) => {
  const contentRef = useRef(null);

  // Process markdown content with memoization for better performance
  const processedContent = useMemo(() => {
    return processMarkdown(content);
  }, [content]);
  
  useEffect(() => {
    if (contentRef.current) {
      // Initialize syntax highlighting
      contentRef.current.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightBlock(block);
      });
      
      // Add copy buttons to code blocks
      contentRef.current.querySelectorAll('.code-block-container').forEach(container => {
        if (!container.querySelector('.copy-code-button')) {
          const button = document.createElement('button');
          button.className = 'copy-code-button';
          button.setAttribute('aria-label', 'Copy code to clipboard');
          button.addEventListener('click', () => {
            const code = container.querySelector('code').textContent;
            navigator.clipboard.writeText(code)
              .then(() => {
                button.classList.add('copied');
                button.setAttribute('aria-label', 'Copied!');
                setTimeout(() => {
                  button.classList.remove('copied');
                  button.setAttribute('aria-label', 'Copy code to clipboard');
                }, 2000);
              })
              .catch(err => {
                console.error('Could not copy code: ', err);
              });
          });
          container.appendChild(button);
        }
      });
      
      // Add special handling for file icons
      contentRef.current.querySelectorAll('p').forEach(p => {
        if (p.textContent.startsWith('📄') || p.textContent.startsWith('📝')) {
          p.classList.add('file-header');
        }
      });
    }
  }, [content]);

  // Configure marked
  marked.setOptions({
    gfm: true,
    breaks: true,
    tables: true,
    smartLists: true,
    smartypants: true,
    highlight: function(code, lang) {
      if (lang && hljs.getLanguage(lang)) {
        try {
          return hljs.highlight(lang, code).value;
        } catch (e) {
          console.error(e);
        }
      }
      return hljs.highlightAuto(code).value;
    }
  });

  // Custom renderer to wrap code blocks with container for copy button
  const renderer = new marked.Renderer();
  const originalCodeRenderer = renderer.code;
  renderer.code = function(code, language, isEscaped) {
    const renderedCode = originalCodeRenderer.call(this, code, language, isEscaped);
    return `<div class="code-block-container">${renderedCode}</div>`;
  };

  // Process markdown content
  function processMarkdown(content) {
    // Handle emoji styling
    const regex = emojiRegex();
    const contentWithStyledEmojis = content.replace(regex, (match) => 
      `<span class="emoji">${match}</span>`
    );
    
    // Convert markdown to HTML
    const rawMarkup = marked(contentWithStyledEmojis, { renderer });
    
    // Sanitize HTML
    const cleanMarkup = DOMPurify.sanitize(rawMarkup, {
      ALLOWED_TAGS: ['p', 'b', 'i', 'em', 'strong', 'h1', 'h2', 'h3', 'table', 
                     'tr', 'td', 'th', 'thead', 'tbody', 'img', 'a', 'ul', 'ol', 
                     'li', 'code', 'pre', 'span', 'div', 'button'],
      ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'class', 'id', 'aria-label']
    });
    
    return cleanMarkup;
  };

  return (
    <div 
      className="markdown-content"
      ref={contentRef}
      dangerouslySetInnerHTML={{ __html: processedContent }}
    />
  );
};

export default MarkdownRenderer;
