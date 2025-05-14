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

// トークン管理クラス
class TokenManager {
    constructor() {
        this.tokenKey = 'access_token';
        this.refreshTokenKey = 'refresh_token';
        this.tokenExpiryKey = 'token_expiry';
    }

    // トークンの保存
    saveTokens(accessToken, refreshToken, expiresIn) {
        const expiryTime = Date.now() + (expiresIn * 1000);
        sessionStorage.setItem(this.tokenKey, accessToken);
        sessionStorage.setItem(this.refreshTokenKey, refreshToken);
        sessionStorage.setItem(this.tokenExpiryKey, expiryTime.toString());
    }

    // トークンの取得
    getAccessToken() {
        return sessionStorage.getItem(this.tokenKey);
    }

    // トークンの有効期限チェック
    isTokenExpired() {
        const expiryTime = sessionStorage.getItem(this.tokenExpiryKey);
        if (!expiryTime) return true;
        return Date.now() >= parseInt(expiryTime);
    }

    // トークンの更新が必要かチェック
    shouldRefreshToken() {
        const expiryTime = sessionStorage.getItem(this.tokenExpiryKey);
        if (!expiryTime) return true;
        // 有効期限の5分前から更新を開始
        return Date.now() >= (parseInt(expiryTime) - 5 * 60 * 1000);
    }

    // トークンの削除
    clearTokens() {
        sessionStorage.removeItem(this.tokenKey);
        sessionStorage.removeItem(this.refreshTokenKey);
        sessionStorage.removeItem(this.tokenExpiryKey);
    }
}

// トークンマネージャーのインスタンスを作成
const tokenManager = new TokenManager();

// トークンの更新
async function refreshAccessToken() {
    try {
        const refreshToken = sessionStorage.getItem('refresh_token');
        if (!refreshToken) {
            throw new Error('リフレッシュトークンがありません');
        }

        const response = await fetch('/refresh-token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh_token: refreshToken })
        });

        if (!response.ok) {
            throw new Error('トークンの更新に失敗しました');
        }

        const data = await response.json();
        tokenManager.saveTokens(
            data.access_token,
            data.refresh_token,
            data.expires_in
        );

        return data.access_token;
    } catch (error) {
        console.error('トークン更新エラー:', error);
        tokenManager.clearTokens();
        window.location.href = '/login?session_expired=true';
        throw error;
    }
}

// 定期的なトークン更新チェック
function startTokenRefreshCheck() {
    setInterval(async () => {
        if (tokenManager.shouldRefreshToken()) {
            try {
                await refreshAccessToken();
            } catch (error) {
                console.error('トークン更新チェックエラー:', error);
            }
        }
    }, 60000); // 1分ごとにチェック
}

// 既存の関数を更新
function getAuthHeader() {
    const token = tokenManager.getAccessToken();
    return token ? { 'Authorization': `Bearer ${token}` } : {};
}

function isTokenValid() {
    return !tokenManager.isTokenExpired();
}

// トークン更新チェックを開始
startTokenRefreshCheck();

export {
  getAuthHeaders,
  fetchCRMData,
  submitFormData,
  loadConversationHistory,
  sendChatMessage,
  clearChatHistory,
  validateToken
};