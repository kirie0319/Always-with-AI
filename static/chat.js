// DOM elements
const chatBox = document.getElementById('chat-box');
const inputField = document.getElementById('input');
const sendButton = document.getElementById('send-btn');

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
  inputField.focus();

  // Submit on Enter key
  inputField.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      send();
    }
  });
});

// Format timestamp
function formatTimestamp() {
  const now = new Date();
  const hours = now.getHours().toString().padStart(2, '0');
  const minutes = now.getMinutes().toString().padStart(2, '0');
  return `${hours}:${minutes}`;
}

// Add message to chat
function appendMessage(role, text) {
  const timestamp = formatTimestamp();

  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${role === 'user' ? 'user' : 'bot'}`;

  // Create avatar
  const avatarDiv = document.createElement('div');
  avatarDiv.className = 'avatar';
  const avatarIcon = document.createElement('i');

  if (role === 'user') {
    avatarIcon.className = 'fas fa-user';
  } else {
    avatarIcon.className = 'fas fa-robot';
  }

  avatarDiv.appendChild(avatarIcon);

  // Create message content
  const contentDiv = document.createElement('div');
  contentDiv.className = 'message-content';

  const messagePara = document.createElement('p');
  messagePara.textContent = text;

  const timeSpan = document.createElement('span');
  timeSpan.className = 'timestamp';
  timeSpan.textContent = timestamp;

  contentDiv.appendChild(messagePara);
  contentDiv.appendChild(timeSpan);

  // Assemble message
  messageDiv.appendChild(avatarDiv);
  messageDiv.appendChild(contentDiv);

  // Add to chat
  chatBox.appendChild(messageDiv);

  // Scroll to bottom
  scrollToBottom();
}

// Show typing indicator
function showTyping() {
  const typingDiv = document.createElement('div');
  typingDiv.className = 'message bot typing-message';
  typingDiv.innerHTML = `
    <div class="avatar">
      <i class="fas fa-robot"></i>
    </div>
    <div class="message-content">
      <div class="typing">
        <span></span>
        <span></span>
        <span></span>
      </div>
    </div>
  `;

  chatBox.appendChild(typingDiv);
  scrollToBottom();
  return typingDiv;
}

// Scroll chat to bottom
function scrollToBottom() {
  chatBox.scrollTop = chatBox.scrollHeight;
}

// Remove typing indicator
function removeTypingIndicator() {
  const typingMessage = document.querySelector('.typing-message');
  if (typingMessage) {
    chatBox.removeChild(typingMessage);
  }
}

// Send message to server
async function send() {
  const text = inputField.value.trim();
  if (!text) return;

  // Clear input
  inputField.value = '';
  inputField.focus();

  // Add user message to chat
  appendMessage('user', text);

  // Show typing indicator
  const typingIndicator = showTyping();

  try {
    // Send to server
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text })
    });

    if (!res.ok) {
      throw new Error('Network response was not ok');
    }

    const data = await res.json();

    // Remove typing indicator
    removeTypingIndicator();

    // Add bot response
    appendMessage('ai', data.response);
  } catch (error) {
    console.error('Error:', error);
    removeTypingIndicator();
    appendMessage('ai', 'すみません、エラーが発生しました。もう一度お試しください。');
  }
}

// Clear chat history
async function clearChat() {
  if (!confirm('チャット履歴をクリアしますか？')) return;

  try {
    const res = await fetch('/clear', { method: 'POST' });
    const data = await res.json();

    // Clear UI
    chatBox.innerHTML = '';

    // Add welcome message
    appendMessage('ai', 'こんにちは！Ninja.AIです。日本のレストランについて何でも聞いてください。おすすめの寿司屋さんや、本格的なラーメン店など、お手伝いします！');

  } catch (error) {
    console.error('Error clearing chat:', error);
    alert('チャットのクリアに失敗しました。もう一度お試しください。');
  }
}