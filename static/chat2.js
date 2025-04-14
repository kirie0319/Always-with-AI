// chat2.js
document.addEventListener('DOMContentLoaded', function () {
  // DOM要素の取得
  const chatMessages = document.getElementById('chat-messages');
  const userInput = document.getElementById('user-input');
  const sendButton = document.getElementById('send-button');
  const clearChatButton = document.getElementById('clear-chat');
  const providerSelect = document.getElementById('provider-select');
  const modelSelect = document.getElementById('model-select');
  const promptCategorySelect = document.getElementById('prompt-category');
  const promptNameSelect = document.getElementById('prompt-name');
  const toggleSidebarBtn = document.getElementById('toggle-sidebar-btn');
  const sidebar = document.querySelector('.sidebar');
  const anthropicStatus = document.getElementById('anthropic-status');
  const openaiStatus = document.getElementById('openai-status');

  // 状態管理
  let availableProviders = [];
  let availableModels = {};
  let availablePrompts = {};
  let isProcessing = false;

  // 初期化
  initializeUI();

  // イベントリスナー設定
  sendButton.addEventListener('click', sendMessage);
  userInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  clearChatButton.addEventListener('click', clearChat);

  providerSelect.addEventListener('change', function () {
    updateModelOptions();
    localStorage.setItem('selectedProvider', providerSelect.value);
  });

  promptCategorySelect.addEventListener('change', function () {
    updatePromptNameOptions();
    localStorage.setItem('selectedPromptCategory', promptCategorySelect.value);
  });

  modelSelect.addEventListener('change', function () {
    localStorage.setItem('selectedModel', modelSelect.value);
  });

  promptNameSelect.addEventListener('change', function () {
    localStorage.setItem('selectedPromptName', promptNameSelect.value);
  });

  toggleSidebarBtn.addEventListener('click', function () {
    sidebar.classList.toggle('open');
  });

  // UI初期化
  async function initializeUI() {
    await fetchProviders();
    await fetchPrompts();
    loadChatHistory();
    restoreUserPreferences();

    // スマホの場合、初期状態ではサイドバーを閉じる
    if (window.innerWidth <= 768) {
      sidebar.classList.remove('open');
    }
  }

  // ユーザー設定の復元
  function restoreUserPreferences() {
    const savedProvider = localStorage.getItem('selectedProvider');
    const savedModel = localStorage.getItem('selectedModel');
    const savedCategory = localStorage.getItem('selectedPromptCategory');
    const savedPromptName = localStorage.getItem('selectedPromptName');

    if (savedProvider && availableProviders.includes(savedProvider)) {
      providerSelect.value = savedProvider;
      updateModelOptions();

      if (savedModel && availableModels[savedProvider] &&
        availableModels[savedProvider].includes(savedModel)) {
        modelSelect.value = savedModel;
      }
    }

    if (savedCategory && availablePrompts[savedCategory]) {
      promptCategorySelect.value = savedCategory;
      updatePromptNameOptions();

      if (savedPromptName && availablePrompts[savedCategory].includes(savedPromptName)) {
        promptNameSelect.value = savedPromptName;
      }
    }
  }

  // プロバイダー情報の取得
  async function fetchProviders() {
    try {
      const response = await fetch('/providers');
      if (!response.ok) {
        throw new Error('APIの応答が不正です');
      }

      const data = await response.json();

      availableProviders = data.providers;
      availableModels = data.models;

      // プロバイダー選択肢の設定
      providerSelect.innerHTML = '';
      availableProviders.forEach(provider => {
        const option = document.createElement('option');
        option.value = provider;
        option.textContent = providerNameDisplay(provider);
        providerSelect.appendChild(option);
      });

      // プロバイダー状態の更新
      updateProviderStatus();

      // モデル選択肢の更新
      updateModelOptions();
    } catch (error) {
      console.error('プロバイダー情報の取得に失敗:', error);
      showErrorMessage('AIプロバイダーの情報を取得できませんでした。');
    }
  }

  // プロバイダー状態の更新
  function updateProviderStatus() {
    if (availableProviders.includes('anthropic')) {
      anthropicStatus.classList.add('active');
      anthropicStatus.classList.remove('inactive');
    } else {
      anthropicStatus.classList.remove('active');
      anthropicStatus.classList.add('inactive');
    }

    if (availableProviders.includes('openai')) {
      openaiStatus.classList.add('active');
      openaiStatus.classList.remove('inactive');
    } else {
      openaiStatus.classList.remove('active');
      openaiStatus.classList.add('inactive');
    }
  }

  // モデル選択肢の更新
  function updateModelOptions() {
    const selectedProvider = providerSelect.value;
    modelSelect.innerHTML = '';

    if (availableModels[selectedProvider]) {
      availableModels[selectedProvider].forEach(model => {
        const option = document.createElement('option');
        option.value = model;
        option.textContent = model;
        modelSelect.appendChild(option);
      });
    }
  }

  // プロンプト情報の取得
  async function fetchPrompts() {
    try {
      const response = await fetch('/prompts');
      if (!response.ok) {
        throw new Error('プロンプト情報の応答が不正です');
      }

      availablePrompts = await response.json();

      // プロンプトカテゴリの設定
      promptCategorySelect.innerHTML = '';
      Object.keys(availablePrompts).forEach(category => {
        const option = document.createElement('option');
        option.value = category;
        option.textContent = categoryNameDisplay(category);
        promptCategorySelect.appendChild(option);
      });

      // プロンプト名の更新
      updatePromptNameOptions();
    } catch (error) {
      console.error('プロンプト情報の取得に失敗:', error);
      showErrorMessage('プロンプトテンプレートの情報を取得できませんでした。');
    }
  }

  // プロンプト名選択肢の更新
  function updatePromptNameOptions() {
    const selectedCategory = promptCategorySelect.value;
    promptNameSelect.innerHTML = '';

    if (availablePrompts[selectedCategory]) {
      availablePrompts[selectedCategory].forEach(promptName => {
        const option = document.createElement('option');
        option.value = promptName;
        option.textContent = promptNameDisplay(promptName);
        promptNameSelect.appendChild(option);
      });
    }
  }

  // チャット履歴の読み込み
  function loadChatHistory() {
    // ここでAPIからチャット履歴を取得する実装も可能
    // 現在は空のチャットから開始
    chatMessages.innerHTML = '';

    // ウェルカムメッセージの表示
    const welcomeDiv = document.createElement('div');
    welcomeDiv.className = 'message system-message';
    welcomeDiv.textContent = 'AIアシスタントへようこそ。どのようなことでもお気軽にお尋ねください。';
    chatMessages.appendChild(welcomeDiv);
  }

  // メッセージ送信
  async function sendMessage() {
    const message = userInput.value.trim();
    if (!message || isProcessing) return;

    isProcessing = true;

    // ユーザーメッセージをチャットに追加
    addMessageToChat('user', message);
    userInput.value = '';
    userInput.style.height = 'auto'; // 高さをリセット

    // 入力中インジケーターの表示
    const typingIndicator = document.createElement('div');
    typingIndicator.className = 'typing-indicator';
    typingIndicator.innerHTML = '<span></span><span></span><span></span>';
    chatMessages.appendChild(typingIndicator);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: message,
          provider: providerSelect.value,
          model: modelSelect.value,
          prompt_category: promptCategorySelect.value,
          prompt_name: promptNameSelect.value
        })
      });

      if (!response.ok) {
        throw new Error('サーバーからのレスポンスが不正です');
      }

      const data = await response.json();

      // 入力中インジケーターの削除
      typingIndicator.remove();

      // アシスタントメッセージをチャットに追加
      addMessageToChat('assistant', data.response, {
        timestamp: data.timestamp,
        provider: data.provider,
        model: data.model
      });
    } catch (error) {
      console.error('メッセージ送信エラー:', error);

      // 入力中インジケーターの削除
      typingIndicator.remove();

      // エラーメッセージの表示
      const errorDiv = document.createElement('div');
      errorDiv.className = 'message assistant-message error-message';
      errorDiv.textContent = 'メッセージの処理中にエラーが発生しました。もう一度お試しください。';
      chatMessages.appendChild(errorDiv);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    } finally {
      isProcessing = false;

      // 送信後に入力欄にフォーカス
      setTimeout(() => {
        userInput.focus();
      }, 100);
    }
  }

  // チャットへのメッセージ追加
  function addMessageToChat(role, content, metadata = {}) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;

    // メッセージ内容のフォーマット
    const formattedContent = formatMessageContent(content);
    messageDiv.innerHTML = formattedContent;

    // タイムスタンプの追加
    if (metadata.timestamp) {
      const timestamp = new Date(metadata.timestamp);
      const timestampSpan = document.createElement('span');
      timestampSpan.className = 'timestamp';
      timestampSpan.textContent = formatTime(timestamp);
      messageDiv.appendChild(timestampSpan);
    } else {
      // メタデータがない場合は現在時刻を使用
      const timestamp = new Date();
      const timestampSpan = document.createElement('span');
      timestampSpan.className = 'timestamp';
      timestampSpan.textContent = formatTime(timestamp);
      messageDiv.appendChild(timestampSpan);
    }

    // プロバイダー/モデル情報の追加
    if (role === 'assistant' && metadata.provider && metadata.model) {
      const providerInfoSpan = document.createElement('span');
      providerInfoSpan.className = 'provider-info';
      providerInfoSpan.textContent = `${providerNameDisplay(metadata.provider)} / ${metadata.model}`;
      messageDiv.appendChild(providerInfoSpan);
    }

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // メッセージ内容のフォーマット
  function formatMessageContent(content) {
    // コードブロックの置換
    content = content.replace(/```([\s\S]*?)```/g, (match, code) => {
      return `<pre><code>${escapeHtml(code)}</code></pre>`;
    });

    // インラインコードの置換
    content = content.replace(/`([^`]+)`/g, (match, code) => {
      return `<code>${escapeHtml(code)}</code>`;
    });

    // 太字テキストの置換
    content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // イタリックテキストの置換
    content = content.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // 順序なしリストの置換
    content = content.replace(/^- (.*?)$/gm, '<li>$1</li>');
    content = content.replace(/<li>.*?<\/li>(?=\n<li>|$)/gs, '<ul>$&</ul>');

    // 順序付きリストの置換
    content = content.replace(/^\d+\. (.*?)$/gm, '<li>$1</li>');
    content = content.replace(/<li>.*?<\/li>(?=\n<li>|$)/gs, '<ol>$&</ol>');

    // 見出しの置換
    content = content.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
    content = content.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
    content = content.replace(/^# (.*?)$/gm, '<h1>$1</h1>');

    // 段落の追加
    const paragraphs = content.split(/\n\n+/);
    if (paragraphs.length > 1) {
      content = paragraphs.map(p => {
        if (
          !p.startsWith('<h1>') &&
          !p.startsWith('<h2>') &&
          !p.startsWith('<h3>') &&
          !p.startsWith('<ul>') &&
          !p.startsWith('<ol>') &&
          !p.startsWith('<pre>')
        ) {
          return `<p>${p}</p>`;
        }
        return p;
      }).join('');
    }

    // 改行の置換（段落以外）
    content = content.replace(/\n(?!<\/p>|<h|<\/h|<ul|<\/ul|<ol|<\/ol|<pre|<\/pre)/g, '<br>');

    return content;
  }

  // HTML特殊文字のエスケープ
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // 時間フォーマット
  function formatTime(date) {
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}`;
  }

  // 日付フォーマット
  function formatDate(date) {
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    return `${year}/${month}/${day}`;
  }

  // プロバイダー名の表示形式
  function providerNameDisplay(provider) {
    const displayNames = {
      'anthropic': 'Anthropic',
      'openai': 'OpenAI'
    };
    return displayNames[provider] || provider.charAt(0).toUpperCase() + provider.slice(1);
  }

  // カテゴリ名の表示形式
  function categoryNameDisplay(category) {
    const displayNames = {
      'general': '一般的な会話',
      'specific': '特化型会話',
      'system': 'システム'
    };
    return displayNames[category] || category.charAt(0).toUpperCase() + category.slice(1);
  }

  // プロンプト名の表示形式
  function promptNameDisplay(promptName) {
    const displayNames = {
      'chat': '一般チャット',
      'finance': '金融アドバイザー',
      'summarizer': '会話要約'
    };
    return displayNames[promptName] || promptName.split('_').map(word =>
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  }

  // エラーメッセージの表示
  function showErrorMessage(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'message system-message error-message';
    errorDiv.textContent = message;
    chatMessages.appendChild(errorDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // チャット履歴のクリア
  async function clearChat() {
    if (!confirm('チャット履歴をクリアしますか？この操作は元に戻せません。')) {
      return;
    }

    try {
      const response = await fetch('/clear', {
        method: 'POST'
      });

      if (!response.ok) {
        throw new Error('クリア操作に失敗しました');
      }

      const data = await response.json();
      chatMessages.innerHTML = '';

      // 成功メッセージの表示
      const systemDiv = document.createElement('div');
      systemDiv.className = 'message system-message';
      systemDiv.textContent = data.message || 'チャット履歴がクリアされました。';
      chatMessages.appendChild(systemDiv);
    } catch (error) {
      console.error('チャットクリアエラー:', error);
      showErrorMessage('チャット履歴のクリアに失敗しました。');
    }
  }

  // ウィンドウサイズ変更時の処理
  window.addEventListener('resize', function () {
    if (window.innerWidth > 768) {
      sidebar.classList.remove('open');
    }
  });

  // モバイルでのタッチイベント処理
  document.addEventListener('touchstart', function (e) {
    if (window.innerWidth <= 768 && sidebar.classList.contains('open') &&
      !sidebar.contains(e.target) && e.target !== toggleSidebarBtn) {
      sidebar.classList.remove('open');
    }
  });

  // デバイス検出
  function isMobileDevice() {
    return (window.innerWidth <= 768) ||
      (navigator.userAgent.match(/Android/i) ||
        navigator.userAgent.match(/webOS/i) ||
        navigator.userAgent.match(/iPhone/i) ||
        navigator.userAgent.match(/iPad/i) ||
        navigator.userAgent.match(/iPod/i) ||
        navigator.userAgent.match(/BlackBerry/i) ||
        navigator.userAgent.match(/Windows Phone/i));
  }

  // テキストエリアの自動リサイズ
  userInput.addEventListener('input', function () {
    // 最小の高さにリセット
    this.style.height = 'auto';

    // スクロールの高さに基づいて高さを設定（最大100pxまで）
    const newHeight = Math.min(this.scrollHeight, 100);
    this.style.height = newHeight + 'px';
  });

  // 初期状態でフォーカスを入力欄に設定
  setTimeout(() => {
    userInput.focus();
  }, 500);

  // メッセージ長の制限チェック
  userInput.addEventListener('keyup', function () {
    const maxLength = 4000; // 最大文字数
    if (this.value.length > maxLength) {
      this.value = this.value.substring(0, maxLength);

      // 警告メッセージ
      if (!document.querySelector('.max-length-warning')) {
        const warningDiv = document.createElement('div');
        warningDiv.className = 'message system-message error-message max-length-warning';
        warningDiv.textContent = `メッセージは最大${maxLength}文字までです。`;
        chatMessages.appendChild(warningDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // 警告メッセージは3秒後に消える
        setTimeout(() => {
          const warning = document.querySelector('.max-length-warning');
          if (warning) {
            warning.remove();
          }
        }, 3000);
      }
    }
  });

  // ダブルクリックでメッセージをコピー
  chatMessages.addEventListener('dblclick', function (e) {
    const messageElement = e.target.closest('.message');
    if (!messageElement) return;

    // プロバイダー情報とタイムスタンプを除外
    const messageText = messageElement.cloneNode(true);
    const timestamp = messageText.querySelector('.timestamp');
    const providerInfo = messageText.querySelector('.provider-info');

    if (timestamp) timestamp.remove();
    if (providerInfo) providerInfo.remove();

    // テキスト選択
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(messageText);
    selection.removeAllRanges();
    selection.addRange(range);

    // クリップボードにコピー
    try {
      document.execCommand('copy');
      // コピー成功通知
      const notification = document.createElement('div');
      notification.className = 'copy-notification';
      notification.textContent = 'メッセージをコピーしました';
      notification.style.position = 'fixed';
      notification.style.bottom = '20px';
      notification.style.left = '50%';
      notification.style.transform = 'translateX(-50%)';
      notification.style.padding = '8px 16px';
      notification.style.backgroundColor = 'rgba(0,0,0,0.7)';
      notification.style.color = 'white';
      notification.style.borderRadius = '4px';
      notification.style.zIndex = '1000';
      document.body.appendChild(notification);

      setTimeout(() => {
        notification.remove();
      }, 2000);
    } catch (err) {
      console.error('コピーに失敗しました:', err);
    }

    // 選択解除
    selection.removeAllRanges();
  });
});