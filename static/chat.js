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

// タブ切り替え関数
function changeTab(index) {
  // すべてのタブからactiveクラスを削除
  const tabs = document.querySelectorAll('.financial-tab-item');
  tabs.forEach(tab => {
    tab.classList.remove('active');
  });

  // クリックされたタブにactiveクラスを追加
  tabs[index].classList.add('active');
}

// Add message to chat - LINE/WhatsAppスタイルのチャット
function appendMessage(role, text) {
  const timestamp = formatTimestamp();
  const messageDiv = document.createElement('div');

  if (role === 'user') {
    messageDiv.className = 'message user';

    // ユーザーアバター
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'avatar';
    const avatarIcon = document.createElement('i');
    avatarIcon.className = 'fas fa-user';
    avatarDiv.appendChild(avatarIcon);

    // メッセージコンテンツ
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = text;

    // タイムスタンプ
    const timeSpan = document.createElement('span');
    timeSpan.className = 'timestamp';
    timeSpan.textContent = timestamp;
    contentDiv.appendChild(timeSpan);

    // メッセージの組み立て
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
  } else {
    messageDiv.className = 'message bot';

    // AIアバター
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'avatar';
    const avatarIcon = document.createElement('i');
    avatarIcon.className = 'fas fa-robot';
    avatarDiv.appendChild(avatarIcon);

    // メッセージコンテンツ
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    // AIメッセージの場合はマークダウンをサポート
    if (text.includes('**')) {
      // マークダウンを含む場合
      const contentInner = document.createElement('div');
      contentInner.className = 'markdown-content';
      contentInner.innerHTML = renderMarkdown(text);

      // コードブロックがあれば、highlight.jsを適用
      if (hljs) {
        contentInner.querySelectorAll('pre code').forEach((block) => {
          hljs.highlightElement(block);
        });
      }

      contentDiv.appendChild(contentInner);
    } else {
      // マークダウンがない場合は段落に分ける
      const paragraphs = text.split('\n\n');

      for (const paragraph of paragraphs) {
        if (paragraph.trim()) {
          const p = document.createElement('p');
          p.textContent = paragraph;
          contentDiv.appendChild(p);
        }
      }
    }

    // タイムスタンプ
    const timeSpan = document.createElement('span');
    timeSpan.className = 'timestamp';
    timeSpan.textContent = timestamp;
    contentDiv.appendChild(timeSpan);

    // メッセージの組み立て
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
  }

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

// プリセットメッセージを送信する機能
function sendPresetMessage(message) {
  // プリセットメッセージをチャットボックスに追加
  appendMessage('user', message);

  // 入力フィールドをクリア
  inputField.value = '';

  // タイピングインジケータを表示
  const typingIndicator = showTyping();

  // サーバーへ送信
  fetch('/chat', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: message })
  })
    .then(response => {
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      return response.json();
    })
    .then(data => {
      // タイピングインジケータを削除
      removeTypingIndicator();

      // AIの応答をチャットボックスに追加
      appendMessage('ai', data.response);

      // プロンプト名の更新（サーバーから返ってきた場合）
      if (data.prompt_name) {
        promptNameElement.textContent = data.prompt_name;
        // セッションストレージに保存
        sessionStorage.setItem('selectedPromptName', data.prompt_name);
      }
    })
    .catch(error => {
      console.error('Error:', error);
      removeTypingIndicator();
      appendMessage('ai', 'すみません、エラーが発生しました。もう一度お試しください。');
    });

  // チャットボックスを一番下までスクロール
  scrollToBottom();
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
    appendMessage('ai', 'こんにちは！Financial Supporter AIです。資産運用やライフプランニングについてお手伝いします。どのようなことでもお気軽にご相談ください。');

  } catch (error) {
    console.error('Error clearing chat:', error);
    alert('チャットのクリアに失敗しました。もう一度お試しください。');
  }
}