/**
 * チャット機能に関連する関数
 * メッセージの表示やチャット操作を担当
 */
import { sendChatMessage, clearChatHistory } from './api-service.js';

// DOM要素の参照
let chatBox;
let inputField;

/**
 * チャット機能の初期化
 */
function initChat() {
  chatBox = document.getElementById('chat-box');
  inputField = document.getElementById('input');
  
  if (!chatBox || !inputField) {
    console.error('チャット要素が見つかりません');
    return;
  }
}

/**
 * タイムスタンプをフォーマットする関数
 * @returns {string} - フォーマットされたタイムスタンプ（例: "12:34"）
 */
function formatTimestamp() {
  const now = new Date();
  const hours = now.getHours().toString().padStart(2, '0');
  const minutes = now.getMinutes().toString().padStart(2, '0');
  return `${hours}:${minutes}`;
}

/**
 * マークダウンをパースして安全に描画する関数
 * @param {string} text - マークダウンテキスト
 * @returns {string} - HTMLに変換されたテキスト
 */
function renderMarkdown(text) {
  // markedが利用可能かチェック
  if (typeof marked !== 'undefined') {
    return marked.parse(text);
  }
  return text;
}

/**
 * テキストがマークダウンを含むかを判定する関数
 * @param {string} text - 判定するテキスト
 * @returns {boolean} - マークダウンを含む場合はtrue
 */
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

/**
 * メッセージをチャットに追加する関数
 * @param {string} role - メッセージの送信者（'user' または 'ai'）
 * @param {string} text - メッセージのテキスト
 */
function appendMessage(role, text) {
  if (!chatBox) {
    console.error('チャットボックスが初期化されていません');
    return;
  }

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
      if (typeof hljs !== 'undefined') {
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

  // チャットボックスにメッセージを追加
  chatBox.appendChild(messageDiv);

  // 下にスクロール
  scrollToBottom();
}

/**
 * タイピングインジケータを表示する関数
 * @returns {Element} - 作成されたタイピングインジケータ要素
 */
function showTyping() {
  if (!chatBox) {
    console.error('チャットボックスが初期化されていません');
    return null;
  }

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

/**
 * タイピングインジケータを削除する関数
 */
function removeTypingIndicator() {
  if (!chatBox) {
    console.error('チャットボックスが初期化されていません');
    return;
  }

  const typingMessage = document.querySelector('.typing-message');
  if (typingMessage) {
    chatBox.removeChild(typingMessage);
  }
}

/**
 * チャットを下にスクロールする関数
 */
function scrollToBottom() {
  if (!chatBox) {
    console.error('チャットボックスが初期化されていません');
    return;
  }

  chatBox.scrollTop = chatBox.scrollHeight;
}

/**
 * メッセージを送信する関数
 * @returns {Promise<void>}
 */
async function send() {
  if (!inputField || !chatBox) {
    console.error('入力フィールドまたはチャットボックスが初期化されていません');
    return;
  }

  const text = inputField.value.trim();
  if (!text) return;

  // 入力フィールドをクリア
  inputField.value = '';
  inputField.focus();

  // ユーザーメッセージをUIに追加
  appendMessage('user', text);

  // テスト用コード - 「test」と入力するとマークダウンテストを実行（開発時のみ）
  if (text.toLowerCase() === 'test') {
    testMarkdownRendering();
    return;
  }

  // 既存のEventSourceがあれば閉じる
  if (window.eventSource) {
    window.eventSource.close();
    window.eventSource = null;
  }

  // ローディング表示
  const typingIndicator = showTyping();

  try {
    // POSTリクエスト
    const response = await sendChatMessage(text);

    if (!response.ok) {
      throw new Error('Error: ' + response.status);
    }

    if (response.headers.get('Content-Type').includes('text/event-stream')) {
      // SSEストリーミングの場合
      processEventStream(response);
    } else {
      // 通常のJSONレスポンスの場合（以前の実装）
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

/**
 * イベントストリームを処理する関数
 * @param {Response} response - サーバーからのレスポンス
 */
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
          if (typeof hljs !== 'undefined') {
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
                chatBox.appendChild(messageDiv);
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

/**
 * デモンストレーション用のテストメッセージ
 */
function testMarkdownRendering() {
  const markdownExamples = [
    "# マークダウンテスト\n\n**太字**と*斜体*と`コード`のテスト。\n\nコードブロック:\n```javascript\nconsole.log('Hello, world!');\n```\n\nリスト:\n- 項目1\n- 項目2\n  - ネストした項目\n\n> これは引用です。\n\n[リンク](https://example.com)",
    "テーブルのテスト:\n\n| 項目 | 価格 |\n|------|------|\n| りんご | 100円 |\n| バナナ | 80円 |"
  ];

  // マークダウンのテストメッセージを表示
  appendMessage('ai', markdownExamples[0]);
  setTimeout(() => {
    appendMessage('ai', markdownExamples[1]);
  }, 1000);
}

/**
 * チャット履歴をクリアする関数
 * @returns {Promise<void>}
 */
async function clearChat() {
  if (!confirm('チャット履歴をクリアしますか？')) return;

  try {
    const data = await clearChatHistory();

    // UIをクリア
    if (chatBox) {
      chatBox.innerHTML = '';
    }

    // ウェルカムメッセージを追加
    appendMessage('ai', 'こんにちは！Financial Supporter AIです。資産運用やライフプランニングについてお手伝いします。どのようなことでもお気軽にご相談ください。');

  } catch (error) {
    console.error('Error clearing chat:', error);
    alert('チャットのクリアに失敗しました。もう一度お試しください。');
  }
}

export {
  initChat,
  formatTimestamp,
  renderMarkdown,
  containsMarkdown,
  appendMessage,
  showTyping,
  removeTypingIndicator,
  scrollToBottom,
  send,
  processEventStream,
  clearChat
};