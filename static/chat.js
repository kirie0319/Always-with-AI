// DOM elements
const chatBox = document.getElementById('chat-box');
const inputField = document.getElementById('input');
const sendButton = document.getElementById('send-btn');
const promptNameElement = document.getElementById('prompt-name');

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
  inputField.focus();

  // マークダウンの設定
  marked.setOptions({
    breaks: true, // 改行をbrタグに変換
    gfm: true,    // GitHub Flavored Markdown を有効化
    highlight: function (code, lang) {
      // コードのハイライト（highlight.jsを使用している場合）
      if (hljs && lang && hljs.getLanguage(lang)) {
        try {
          return hljs.highlight(code, { language: lang }).value;
        } catch (e) { }
      }
      return code;
    }
  });

  // Submit on Enter key
  inputField.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      send();
    }
  });

  // セッションストレージから選択中のプロンプト名を取得して表示
  const selectedPromptName = sessionStorage.getItem('selectedPromptName');
  if (selectedPromptName) {
    promptNameElement.textContent = selectedPromptName;
  }
});

// Format timestamp
function formatTimestamp() {
  const now = new Date();
  const hours = now.getHours().toString().padStart(2, '0');
  const minutes = now.getMinutes().toString().padStart(2, '0');
  return `${hours}:${minutes}`;
}

// マークダウンをパースして安全に描画する関数
function renderMarkdown(text) {
  return marked.parse(text);
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

  const messagePara = document.createElement('div');
  messagePara.className = 'markdown-content';

  // ユーザーの場合はマークダウンパースせず、AIの場合はマークダウンパース
  if (role === 'user') {
    messagePara.textContent = text;
  } else {
    // マークダウンをHTMLに変換
    messagePara.innerHTML = renderMarkdown(text);

    // コードブロックがあれば、highlight.jsを適用
    if (hljs) {
      messagePara.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightElement(block);
      });
    }
  }

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
      credentials: 'same-origin',
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

    // プロンプト名の更新（サーバーから返ってきた場合）
    if (data.prompt_name) {
      promptNameElement.textContent = data.prompt_name;
      // セッションストレージに保存
      sessionStorage.setItem('selectedPromptName', data.prompt_name);
    }
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
    appendMessage('ai', 'こんにちは！Zeals.AIです！意思決定のサポートについて、お手伝いします。');

  } catch (error) {
    console.error('Error clearing chat:', error);
    alert('チャットのクリアに失敗しました。もう一度お試しください。');
  }
}