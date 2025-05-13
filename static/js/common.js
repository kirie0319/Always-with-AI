// 共通機能を提供するJavaScriptファイル

// 認証ヘッダーを取得する関数
function getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    return token ? {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    } : {
      'Content-Type': 'application/json'
    };
  }
  
  // タイムスタンプをフォーマットする関数
  function formatTimestamp() {
    const now = new Date();
    const hours = now.getHours().toString().padStart(2, '0');
    const minutes = now.getMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}`;
  }
  
  // マークダウンをパースして安全に描画する関数
  function renderMarkdown(text) {
    // Note: DOMPurifyを使用している場合はここでサニタイズする
    // return DOMPurify.sanitize(marked.parse(text));
    return marked.parse(text);
  }
  
  // マークダウンかどうかを判定する関数
  function containsMarkdown(text) {
    // 一般的なマークダウン記法をチェック
    const markdownPatterns = [
      /\*\*.*?\*\*/,           // 太字 **bold**
      /\*.*?\*/,               // 斜体 *italic*
      /`.*?`/,                 // インラインコード `code`
      /```[\s\S]*?```/,        // コードブロック ```code```
      /^#+\s+.*/m,             // 見出し # Heading
      /^\s*[-*+]\s+.*/m,       // リスト - item
      /^\s*\d+\.\s+.*/m,       // 数字リスト 1. item
      /\[.*?\]\(.*?\)/,        // リンク [link](url)
      /!\[.*?\]\(.*?\)/,       // 画像 ![alt](url)
      /^\s*>\s+.*/m,           // 引用 > quote
      /^\s*---+\s*$/m,         // 水平線 ---
      /\|\s.*\s\|/             // テーブル | table |
    ];
  
    // いずれかのパターンにマッチすればマークダウンと判定
    return markdownPatterns.some(pattern => pattern.test(text));
  }
  
  // チャットメッセージを追加する関数
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
      if (containsMarkdown(text)) {
        // マークダウンを含む場合
        const contentInner = document.createElement('div');
        contentInner.className = 'markdown-content';
        contentInner.innerHTML = renderMarkdown(text);
  
        // コードブロックがあれば、highlight.jsを適用
        if (window.hljs) {
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
    const chatBox = document.getElementById('chat-box');
    if (chatBox) {
      chatBox.appendChild(messageDiv);
      
      // Scroll to bottom
      scrollToBottom();
    }
  }
  
  // チャットを下部にスクロールする関数
  function scrollToBottom() {
    const chatBox = document.getElementById('chat-box');
    if (chatBox) {
      chatBox.scrollTop = chatBox.scrollHeight;
    }
  }
  
  // タイピングインジケータを表示する関数
  function showTyping() {
    const chatBox = document.getElementById('chat-box');
    if (!chatBox) return null;
    
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
  
  // タイピングインジケータを削除する関数
  function removeTypingIndicator() {
    const typingMessage = document.querySelector('.typing-message');
    if (typingMessage) {
      const chatBox = document.getElementById('chat-box');
      if (chatBox) {
        chatBox.removeChild(typingMessage);
      }
    }
  }
  
  // 会話履歴を読み込む関数
  async function loadConversationHistory() {
    try {
      const response = await fetch('/conversation_history', {
        method: 'GET',
        headers: getAuthHeaders()
      });
  
      if (!response.ok) {
        throw new Error('Error loading conversation history');
      }
  
      const history = await response.json();
  
      history.forEach((msg) => {
        appendMessage(msg.role === "user" ? "user" : "ai", msg.content)
      });
    } catch (error) {
      console.error('Error loading conversation history:', error);
      appendMessage('ai', '申し訳ありません。会話履歴の読み込みに失敗しました。')
    }
  }
  
  // チャットを送信する関数
  async function send() {
    const inputField = document.getElementById('input');
    if (!inputField) return;
    
    const text = inputField.value.trim();
    if (!text) return;
  
    // 入力フィールドをクリア
    inputField.value = '';
    inputField.focus();
  
    // ユーザーメッセージをUIに追加
    appendMessage('user', text);
  
    // 既存のEventSourceがあれば閉じる
    if (window.eventSource) {
      window.eventSource.close();
      window.eventSource = null;
    }
  
    // ローディング表示
    const typingIndicator = showTyping();
  
    try {
      // POSTリクエスト
      const response = await fetch('/chat', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ message: text })
      });
  
      if (!response.ok) {
        throw new Error('Error: ' + response.status);
      }
  
      if (response.headers.get('Content-Type').includes('text/event-stream')) {
        // SSEストリーミングの場合
        processEventStream(response);
      } else {
        // 通常のJSONレスポンスの場合
        const jsonData = await response.json();
        removeTypingIndicator();
        appendMessage('ai', jsonData.response);
      }
    } catch (error) {
      console.error('Error:', error);
      removeTypingIndicator();
      appendMessage('ai', 'すみません、エラーが発生しました。もう一度お試しください。');
    }
  }
  
  // SSEを処理する関数
  function processEventStream(response) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let assistant_text = '';
  
    // メッセージ表示用の要素を作成
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot';
  
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'avatar';
    const avatarIcon = document.createElement('i');
    avatarIcon.className = 'fas fa-robot';
    avatarDiv.appendChild(avatarIcon);
  
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
  
    const contentInner = document.createElement('div');
    contentInner.className = 'markdown-content';
    contentDiv.appendChild(contentInner);
  
    const timeSpan = document.createElement('span');
    timeSpan.className = 'timestamp';
    timeSpan.textContent = formatTimestamp();
    contentDiv.appendChild(timeSpan);
  
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
  
    // 読み込み開始
    read();
  
    function read() {
      reader.read().then(({ done, value }) => {
        if (done) {
          // ストリーム終了、必要なクリーンアップを行う
          removeTypingIndicator();
  
          // マークダウンの完全なレンダリング
          if (containsMarkdown(assistant_text)) {
            contentInner.innerHTML = renderMarkdown(assistant_text);
  
            // コードブロックがあれば、highlight.jsを適用
            if (window.hljs) {
              contentInner.querySelectorAll('pre code').forEach((block) => {
                hljs.highlightElement(block);
              });
            }
          } else {
            // マークダウンがない場合は段落に分ける
            contentInner.innerHTML = '';
            const paragraphs = assistant_text.split('\n\n');
            for (const paragraph of paragraphs) {
              if (paragraph.trim()) {
                const p = document.createElement('p');
                p.textContent = paragraph;
                contentInner.appendChild(p);
              }
            }
          }
  
          return;
        }
  
        // 受信したバイナリデータを文字列に変換して蓄積
        buffer += decoder.decode(value, { stream: true });
  
        // イベントデータを解析
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // 最後の不完全な行は次回処理のために保持
  
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const eventData = JSON.parse(line.substring(6));
  
              if (eventData.text) {
                // 最初のテキストチャンクが来たら、タイピングインジケータを削除しメッセージ要素を追加
                if (!assistant_text) {
                  removeTypingIndicator();
                  const chatBox = document.getElementById('chat-box');
                  if (chatBox) {
                    chatBox.appendChild(messageDiv);
                  }
                }
  
                // テキストを追加
                assistant_text += eventData.text;
  
                // 暫定的なレンダリング（ストリーミング表示）
                if (containsMarkdown(assistant_text)) {
                  contentInner.innerHTML = renderMarkdown(assistant_text);
                } else {
                  contentInner.innerHTML = '';
                  const paragraphs = assistant_text.split('\n\n');
                  for (const paragraph of paragraphs) {
                    if (paragraph.trim()) {
                      const p = document.createElement('p');
                      p.textContent = paragraph;
                      contentInner.appendChild(p);
                    }
                  }
                }
  
                // 自動スクロール
                scrollToBottom();
              }
  
              if (eventData.error) {
                // エラーメッセージの処理
                console.error('Error from server:', eventData.error);
                removeTypingIndicator();
                appendMessage('ai', 'すみません、エラーが発生しました: ' + eventData.error);
              }
  
              if (eventData.complete) {
                // ストリーム完了通知
                console.log('Stream complete');
              }
            } catch (e) {
              console.error('Error parsing event data:', e, line.substring(6));
            }
          }
        }
  
        // 次のチャンクを読み込む
        read();
      }).catch(error => {
        console.error('Error reading stream:', error);
        removeTypingIndicator();
        appendMessage('ai', 'すみません、データの読み込み中にエラーが発生しました。もう一度お試しください。');
      });
    }
  }
  
  // チャット履歴をクリアする関数
  async function clearChat() {
    if (!confirm('チャット履歴をクリアしますか？')) return;
  
    try {
      const res = await fetch('/clear', {
        method: 'POST',
        headers: getAuthHeaders()
      });
      const data = await res.json();
  
      // Clear UI
      const chatBox = document.getElementById('chat-box');
      if (chatBox) {
        chatBox.innerHTML = '';
      }
  
      // Add welcome message
      appendMessage('ai', 'こんにちは！Financial Supporter AIです。資産運用やライフプランニングについてお手伝いします。どのようなことでもお気軽にご相談ください。');
  
    } catch (error) {
      console.error('Error clearing chat:', error);
      alert('チャットのクリアに失敗しました。もう一度お試しください。');
    }
  }