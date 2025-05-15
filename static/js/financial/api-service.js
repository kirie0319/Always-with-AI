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
        console.log('TokenManager initialized');
    }

    // トークンの保存
    saveTokens(accessToken, refreshToken, expiresIn) {
        const expiryTime = Date.now() + (expiresIn * 1000);
        console.log('TokenManager - Saving tokens:', {
            accessToken: accessToken ? `${accessToken.substring(0, 10)}...` : null,
            refreshToken: refreshToken ? `${refreshToken.substring(0, 10)}...` : null,
            expiresIn: expiresIn,
            expiryTime: new Date(expiryTime).toISOString()
        });
        
        if (!accessToken || !refreshToken) {
            console.warn('TokenManager - Warning: Missing tokens:', {
                hasAccessToken: !!accessToken,
                hasRefreshToken: !!refreshToken
            });
        }
        
        localStorage.setItem(this.tokenKey, accessToken);
        localStorage.setItem(this.refreshTokenKey, refreshToken);
        localStorage.setItem(this.tokenExpiryKey, expiryTime.toString());
        
        // 保存後の確認
        console.log('TokenManager - Tokens saved, verification:', {
            accessToken: localStorage.getItem(this.tokenKey) ? 'saved' : 'missing',
            refreshToken: localStorage.getItem(this.refreshTokenKey) ? 'saved' : 'missing',
            expiryTime: localStorage.getItem(this.tokenExpiryKey) ? 'saved' : 'missing'
        });
    }

    // トークンの取得
    getAccessToken() {
        const token = localStorage.getItem(this.tokenKey);
        console.log('Getting access token:', token ? `${token.substring(0, 10)}...` : null);
        return token;
    }

    // トークンの有効期限チェック
    isTokenExpired() {
        const expiryTime = localStorage.getItem(this.tokenExpiryKey);
        const isExpired = !expiryTime || Date.now() >= parseInt(expiryTime);
        console.log('Token expiry check:', {
            expiryTime: expiryTime ? new Date(parseInt(expiryTime)).toISOString() : null,
            currentTime: new Date().toISOString(),
            isExpired
        });
        return isExpired;
    }

    // トークンの更新が必要かチェック
    shouldRefreshToken() {
        const expiryTime = localStorage.getItem(this.tokenExpiryKey);
        const shouldRefresh = !expiryTime || Date.now() >= (parseInt(expiryTime) - 5 * 60 * 1000);
        console.log('Should refresh token check:', {
            expiryTime: expiryTime ? new Date(parseInt(expiryTime)).toISOString() : null,
            currentTime: new Date().toISOString(),
            shouldRefresh
        });
        return shouldRefresh;
    }

    // トークンの削除
    clearTokens() {
        localStorage.removeItem(this.tokenKey);
        localStorage.removeItem(this.refreshTokenKey);
        localStorage.removeItem(this.tokenExpiryKey);
    }
}

// トークンマネージャーのインスタンスを作成
const tokenManager = new TokenManager();

// TokenManagerクラスをエクスポート
export { TokenManager };

// トークンの更新
async function refreshAccessToken(retryCount = 0) {
    const MAX_RETRIES = 3;
    const RETRY_DELAY = 1000; // 1秒

    try {
        console.log('Starting token refresh process');
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
            console.error('No refresh token found in localStorage');
            throw new Error('リフレッシュトークンがありません');
        }

        console.log('Sending refresh token request');
        const response = await fetch('/refresh-token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh_token: refreshToken })
        });

        if (!response.ok) {
            if (retryCount < MAX_RETRIES) {
                console.log(`Token refresh failed, retrying (${retryCount + 1}/${MAX_RETRIES})...`);
                await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
                return refreshAccessToken(retryCount + 1);
            }
            console.error('Token refresh failed after retries:', {
                status: response.status,
                statusText: response.statusText
            });
            throw new Error('トークンの更新に失敗しました');
        }

        const data = await response.json();
        console.log('Token refresh successful:', {
            accessToken: data.access_token ? `${data.access_token.substring(0, 10)}...` : null,
            refreshToken: data.refresh_token ? `${data.refresh_token.substring(0, 10)}...` : null,
            expiresIn: data.expires_in
        });

        tokenManager.saveTokens(
            data.access_token,
            data.refresh_token,
            data.expires_in
        );

        return data.access_token;
    } catch (error) {
        console.error('Token refresh error:', error);
        if (retryCount < MAX_RETRIES) {
            console.log(`Token refresh error, retrying (${retryCount + 1}/${MAX_RETRIES})...`);
            await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
            return refreshAccessToken(retryCount + 1);
        }
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
                console.error('Token refresh check error:', error);
                // エラーが発生しても即座にログアウトせず、次のチェックを待つ
            }
        }
    }, 30000); // 30秒ごとにチェック（より頻繁にチェック）
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