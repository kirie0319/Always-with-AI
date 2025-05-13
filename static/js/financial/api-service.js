/**
 * API通信関連のサービス
 * サーバーとの通信を担当する関数を提供
 */
import config from './config.js';

/**
 * 認証ヘッダーを取得する関数
 * @returns {Object} - HTTP要求ヘッダー
 */
function getAuthHeaders() {
  const token = localStorage.getItem(config.storageKeys.accessToken);
  return token ? {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  } : {
    'Content-Type': 'application/json'
  };
}

/**
 * CRMデータを取得する関数
 * @param {string} cifId - 顧客識別子
 * @returns {Promise<Object>} - 取得したデータ
 */
async function fetchCRMData(cifId) {
  try {
    const response = await fetch(`${config.endpoints.crmData}${cifId}`, {
      method: 'GET',
      headers: getAuthHeaders()
    });
    
    return await response.json();
  } catch (error) {
    console.error('CRMデータ取得エラー:', error);
    throw error;
  }
}

/**
 * フォームデータを送信する関数
 * @param {Object} formData - 送信するフォームデータ
 * @returns {Promise<Object>} - 応答データ
 */
async function submitFormData(formData) {
  try {
    const response = await fetch(config.endpoints.formSubmit, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(formData)
    });
    
    return await response.json();
  } catch (error) {
    console.error('フォーム送信エラー:', error);
    throw error;
  }
}

/**
 * 会話履歴を読み込む関数
 * @returns {Promise<Array>} - 会話履歴データ
 */
async function loadConversationHistory() {
  try {
    const response = await fetch(config.endpoints.conversationHistory, {
      method: 'GET',
      headers: getAuthHeaders()
    });
    
    if (!response.ok) {
      throw new Error('Error loading conversation history');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error loading conversation history:', error);
    throw error;
  }
}

/**
 * チャットメッセージを送信する関数
 * @param {string} message - 送信するメッセージ
 * @returns {Promise<Response>} - サーバーからの応答
 */
async function sendChatMessage(message) {
  try {
    const response = await fetch(config.endpoints.chat, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ message })
    });
    
    return response;
  } catch (error) {
    console.error('Error sending chat message:', error);
    throw error;
  }
}

/**
 * チャット履歴をクリアする関数
 * @returns {Promise<Object>} - 応答データ
 */
async function clearChatHistory() {
  try {
    const response = await fetch(config.endpoints.clear, {
      method: 'POST',
      headers: getAuthHeaders()
    });
    
    return await response.json();
  } catch (error) {
    console.error('Error clearing chat history:', error);
    throw error;
  }
}

/**
 * トークンを検証する関数
 * @returns {Promise<Object>} - 検証結果
 */
async function validateToken() {
  try {
    const token = localStorage.getItem(config.storageKeys.accessToken);
    if (!token) {
      throw new Error('アクセストークンがありません');
    }
    
    const response = await fetch(config.endpoints.validateToken, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    if (!response.ok) {
      throw new Error('トークン検証に失敗しました');
    }
    
    return await response.json();
  } catch (error) {
    console.error('トークン検証エラー:', error);
    throw error;
  }
}

export {
  getAuthHeaders,
  fetchCRMData,
  submitFormData,
  loadConversationHistory,
  sendChatMessage,
  clearChatHistory,
  validateToken
};